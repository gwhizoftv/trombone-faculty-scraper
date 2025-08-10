import requests
from bs4 import BeautifulSoup
import csv
import re

def scrape_music_schools_wikipedia():
    """Scrape the Wikipedia list of music schools in the US"""
    
    url = "https://en.wikipedia.org/wiki/List_of_colleges_and_university_schools_of_music_in_the_United_States"
    
    print("Fetching Wikipedia page...")
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    universities = []
    
    # Find all tables on the page (organized by state)
    tables = soup.find_all('table', class_='wikitable')
    
    print("Found {} tables to process...".format(len(tables)))
    
    for table in tables:
        # Process each row in the table
        rows = table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                # First cell usually contains the school name
                school_cell = cells[0]
                
                # Extract school name and Wikipedia URL from link if available
                link = school_cell.find('a')
                wikipedia_url = None
                if link and link.get('href', '').startswith('/wiki/'):
                    school_name = link.get_text().strip()
                    wikipedia_url = 'https://en.wikipedia.org' + link.get('href')
                else:
                    school_name = school_cell.get_text().strip()
                
                # Clean up the school name
                school_name = re.sub(r'\[.*?\]', '', school_name)  # Remove citation markers
                school_name = school_name.replace('\n', ' ').strip()
                
                # Try to find the actual school website
                website = ''
                if len(cells) >= 3:  # Some tables have website in 3rd column
                    website_cell = cells[2]
                    website_link = website_cell.find('a', class_='external')
                    if website_link and website_link.get('href'):
                        website = website_link.get('href')
                
                # If no website found and we have Wikipedia page, try to extract from there
                if not website and wikipedia_url:
                    website = extract_website_from_wikipedia(wikipedia_url)
                
                # Skip if it's not a real school name
                if school_name and not school_name.startswith('List of'):
                    # Determine if it's a conservatory or university
                    school_type = 'Conservatory' if 'Conservatory' in school_name else 'University'
                    
                    universities.append({
                        'name': school_name,
                        'url': website,
                        'type': school_type
                    })
    
    # Also look for lists in the page content (some schools might be in lists rather than tables)
    content_div = soup.find('div', id='mw-content-text')
    if content_div:
        # Find all list items that might contain school names
        for li in content_div.find_all('li'):
            # Get the first link in the list item
            link = li.find('a')
            if link and link.get('href', '').startswith('/wiki/'):
                text = link.get_text().strip()
                
                # Check if it looks like a school name
                if any(keyword in text for keyword in ['University', 'College', 'Conservatory', 'School of Music', 'Institute']):
                    # Avoid navigation links and meta pages
                    if not any(skip in text for skip in ['List of', 'Category:', 'Template:', 'Wikipedia:', 'Portal:']):
                        # Clean the name
                        text = re.sub(r'\[.*?\]', '', text).strip()
                        
                        # Check if we already have this school
                        if not any(uni['name'] == text for uni in universities):
                            # Try to get website from Wikipedia page
                            wikipedia_url = 'https://en.wikipedia.org' + link.get('href')
                            website = extract_website_from_wikipedia(wikipedia_url)
                            
                            school_type = 'Conservatory' if 'Conservatory' in text else 'University'
                            universities.append({
                                'name': text,
                                'url': website,
                                'type': school_type
                            })
    
    # Remove duplicates
    seen = set()
    unique_universities = []
    for uni in universities:
        if uni['name'] not in seen:
            seen.add(uni['name'])
            unique_universities.append(uni)
    
    # Sort alphabetically
    unique_universities.sort(key=lambda x: x['name'])
    
    return unique_universities

def extract_website_from_wikipedia(wikipedia_url):
    """Extract the official website from a Wikipedia page"""
    try:
        print("  Fetching website from {}...".format(wikipedia_url.split('/')[-1]))
        response = requests.get(wikipedia_url, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the infobox which usually contains the website
        infobox = soup.find('table', class_='infobox')
        if infobox:
            # Look for "Website" row
            for row in infobox.find_all('tr'):
                header = row.find('th')
                if header and 'website' in header.get_text().lower():
                    cell = row.find('td')
                    if cell:
                        link = cell.find('a', class_='external')
                        if link and link.get('href'):
                            return link.get('href')
        
        # Alternative: Look for official website in external links section
        external_links = soup.find('span', id='External_links')
        if external_links:
            section = external_links.find_parent()
            if section:
                next_sibling = section.find_next_sibling()
                if next_sibling and next_sibling.name == 'ul':
                    first_link = next_sibling.find('a', class_='external')
                    if first_link and 'official' in first_link.get_text().lower():
                        return first_link.get('href')
    
    except Exception as e:
        print("    Could not fetch website: {}".format(str(e)[:50]))
    
    return ''

def save_to_csv(universities, filename='music_schools_wikipedia.csv'):
    """Save the universities list to CSV in the correct format"""
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Use the exact header format expected by the scraper
        writer.writerow(['University Name', 'URL', 'Type'])
        
        for uni in universities:
            writer.writerow([uni['name'], uni['url'], uni['type']])
    
    print("\n✓ Saved {} universities to {}".format(len(universities), filename))

def main():
    """Main function to run the scraper"""
    
    print("="*60)
    print("WIKIPEDIA MUSIC SCHOOLS SCRAPER")
    print("="*60)
    
    # Scrape the Wikipedia page
    universities = scrape_music_schools_wikipedia()
    
    if universities:
        print("\n✓ Found {} music schools/universities".format(len(universities)))
        
        # Show a sample
        print("\nFirst 10 schools found:")
        for uni in universities[:10]:
            print("  • {} ({})".format(uni['name'], uni['type']))
        
        # Save to CSV
        save_to_csv(universities)
        
        # Also create a version with just major conservatories
        conservatories = [uni for uni in universities if uni['type'] == 'Conservatory']
        if conservatories:
            save_to_csv(conservatories, 'conservatories_only.csv')
            print("✓ Also saved {} conservatories to conservatories_only.csv".format(len(conservatories)))
        
        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("1. Review music_schools_wikipedia.csv and remove any non-relevant entries")
        print("2. Run your scraper: python robust_scraper.py music_schools_wikipedia.csv")
        print("3. For testing, use conservatories_only.csv (smaller list)")
        print("="*60)
        
    else:
        print("✗ No universities found. Check your internet connection and try again.")

if __name__ == "__main__":
    # Required packages check
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("Required packages not installed. Please run:")
        print("pip install requests beautifulsoup4")
        exit(1)
    
    main()
