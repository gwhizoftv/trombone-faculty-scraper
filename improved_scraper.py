import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import json
from urllib.parse import urljoin, urlparse
from pathlib import Path
try:
    from googlesearch import search
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    print("Warning: googlesearch-python not installed. Auto URL discovery disabled.")

class ImprovedTromboneScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.results = []
        self.failed_universities = []
    
    def load_universities_from_file(self, filename):
        """Load universities from CSV, JSON, or TXT file"""
        universities = []
        file_path = Path(filename)
        
        if not file_path.exists():
            print(f"Error: File '{filename}' not found!")
            return universities
        
        file_extension = file_path.suffix.lower()
        
        try:
            if file_extension == '.csv':
                with open(filename, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        name = row.get('University Name', row.get('name', ''))
                        url = row.get('URL', row.get('url', ''))
                        is_music_school = row.get('Type', '').lower() == 'conservatory'
                        
                        if name:
                            universities.append({
                                'name': name.strip(),
                                'url': url.strip() if url else None,
                                'is_music_school': is_music_school
                            })
            
            elif file_extension == '.json':
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for uni in data.get('universities', []):
                        universities.append({
                            'name': uni.get('name', ''),
                            'url': uni.get('url'),
                            'is_music_school': uni.get('type', '').lower() == 'conservatory'
                        })
            
            elif file_extension == '.txt':
                with open(filename, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split('\t') if '\t' in line else line.split(',')
                            name = parts[0].strip()
                            url = parts[1].strip() if len(parts) > 1 else None
                            is_music_school = parts[2].strip().lower() == 'conservatory' if len(parts) > 2 else False
                            
                            universities.append({
                                'name': name,
                                'url': url,
                                'is_music_school': is_music_school
                            })
            
            print(f"✓ Loaded {len(universities)} universities from {filename}")
            return universities
            
        except Exception as e:
            print(f"Error loading file '{filename}': {e}")
            return universities
    
    def find_university_url(self, university_name):
        """Use Google to find the university's main website"""
        if not GOOGLE_SEARCH_AVAILABLE:
            return None
            
        try:
            query = f"{university_name} official website"
            for url in search(query, num_results=3):
                if '.edu' in url or '.ac.' in url:
                    return url
        except Exception as e:
            print(f"  Could not find URL for {university_name}: {e}")
        return None
    
    def extract_emails(self, text):
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        # Filter out common non-personal emails
        return [e for e in emails if not any(x in e.lower() for x in ['example', 'domain', 'email', 'your'])]
    
    def extract_name_near_trombone(self, soup, page_text):
        """Extract faculty names near trombone mentions"""
        results = []
        
        # Strategy 1: Look for structured faculty listings
        faculty_cards = soup.find_all(['div', 'article', 'li'], class_=re.compile('faculty|staff|people|profile|member', re.I))
        
        for card in faculty_cards:
            card_text = card.get_text()
            if 'trombone' in card_text.lower():
                # Look for name in headers or strong tags
                name_elem = card.find(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'a'])
                if name_elem:
                    name = name_elem.get_text().strip()
                    # Basic name validation
                    if self.is_valid_name(name):
                        emails = self.extract_emails(card_text)
                        results.append({
                            'name': name,
                            'email': emails[0] if emails else None,
                            'context': card_text[:200]
                        })
        
        # Strategy 2: Look for patterns like "John Smith, trombone" or "trombone - John Smith"
        patterns = [
            r'([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+(?:-[A-Z][a-z]+)?),?\s*(?:–|-|,)?\s*[Tt]rombone',
            r'[Tt]rombone\s*(?:–|-|:)\s*([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+(?:-[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s*\([Tt]rombone\)',
            r'([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s+[Tt]rombone\s+[Ff]aculty',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                if self.is_valid_name(match):
                    # Find email near this name
                    name_index = page_text.find(match)
                    context = page_text[max(0, name_index-200):name_index+200]
                    emails = self.extract_emails(context)
                    
                    results.append({
                        'name': match,
                        'email': emails[0] if emails else None,
                        'context': context[:200]
                    })
        
        # Strategy 3: Find trombone links and check the linked pages
        trombone_links = soup.find_all('a', string=re.compile('trombone', re.I))
        for link in trombone_links[:3]:  # Limit to avoid too many requests
            if link.get('href') and 'faculty' in link.get('href', '').lower():
                # This might be a direct link to trombone faculty
                link_text = link.get_text().strip()
                if self.is_valid_name(link_text):
                    results.append({
                        'name': link_text,
                        'email': None,
                        'profile_url': urljoin(soup.url if hasattr(soup, 'url') else '', link['href'])
                    })
        
        return results
    
    def is_valid_name(self, text):
        """Validate if text is likely a person's name"""
        if not text or len(text) < 5 or len(text) > 50:
            return False
        
        # Must have at least 2 parts
        parts = text.split()
        if len(parts) < 2 or len(parts) > 5:
            return False
        
        # Filter out common non-names
        non_name_words = {
            'faculty', 'staff', 'department', 'school', 'college', 'university',
            'music', 'brass', 'trombone', 'professor', 'instructor', 'lecturer',
            'clear', 'search', 'filter', 'results', 'loading', 'welcome',
            'undergraduate', 'graduate', 'diploma', 'degree', 'bachelor', 'master',
            'performance', 'ensemble', 'orchestra', 'symphony', 'philharmonic',
            'apply', 'contact', 'about', 'more', 'read', 'click', 'here'
        }
        
        text_lower = text.lower()
        for word in non_name_words:
            if word in text_lower:
                return False
        
        # Check capitalization
        for part in parts:
            if part and not (part[0].isupper() or (len(part) <= 3 and part.lower() in ['de', 'van', 'von', 'la', 'le'])):
                return False
        
        return True
    
    def find_faculty_pages(self, base_url, is_music_school=False):
        """Find relevant faculty pages"""
        found_pages = []
        
        # Different search paths for conservatories vs universities
        if is_music_school:
            paths = [
                '/faculty', '/people', '/faculty-staff', '/directory',
                '/brass', '/brass-faculty', '/winds-brass-percussion',
                '/instrumental-studies', '/performance-faculty'
            ]
        else:
            # For universities, try music department paths
            paths = [
                '/music/faculty', '/music/people', '/music/directory',
                '/school-of-music/faculty', '/som/faculty',
                '/music/brass', '/music/faculty/brass',
                '/music-department/faculty', '/college-of-music/faculty'
            ]
        
        for path in paths:
            try:
                url = urljoin(base_url, path)
                response = self.session.get(url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_text = soup.get_text().lower()
                    
                    # Check if this looks like a faculty page
                    if any(word in page_text for word in ['faculty', 'people', 'staff', 'instructor', 'professor']):
                        found_pages.append(response.url)
                        print(f"  ✓ Found faculty page: {response.url}")
                        
                        # If it's specifically brass or has trombone, prioritize it
                        if 'brass' in page_text or 'trombone' in page_text:
                            return [response.url]  # Return immediately, this is what we want
                        
            except Exception as e:
                continue
        
        return found_pages[:3]  # Return top 3 pages to check
    
    def scrape_page_for_trombone(self, url):
        """Scrape a specific page for trombone faculty"""
        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            soup.url = response.url  # Store URL for reference
            page_text = soup.get_text()
            
            if 'trombone' in page_text.lower():
                print(f"    Found 'trombone' mention at: {url}")
                results = self.extract_name_near_trombone(soup, page_text)
                if results:
                    return results[0]  # Return the first/best match
            
            return None
            
        except Exception as e:
            print(f"    Error accessing {url}: {e}")
            return None
    
    def scrape_university(self, uni_info):
        """Main method to scrape a university website"""
        name = uni_info['name']
        base_url = uni_info['url']
        is_music_school = uni_info.get('is_music_school', False)
        
        print(f"\n{'='*60}")
        print(f"Scraping {name}...")
        if is_music_school:
            print(f"  (Identified as music conservatory)")
        
        # Find URL if not provided
        if not base_url:
            print(f"  Looking up URL for {name}...")
            base_url = self.find_university_url(name)
            if not base_url:
                print(f"  ✗ Could not find URL for {name}")
                self.failed_universities.append(name)
                return
            print(f"  ✓ Found: {base_url}")
        
        # Find faculty pages
        print(f"  Searching for faculty pages...")
        faculty_pages = self.find_faculty_pages(base_url, is_music_school)
        
        if not faculty_pages:
            print(f"  ✗ Could not find faculty pages")
            self.failed_universities.append(name)
            return
        
        # Search each faculty page for trombone teachers
        result = None
        for page_url in faculty_pages:
            result = self.scrape_page_for_trombone(page_url)
            if result:
                result['university'] = name
                result['university_website'] = base_url
                result['faculty_page'] = page_url
                self.results.append(result)
                print(f"  ✓ Found trombone teacher: {result['name']}")
                if result.get('email'):
                    print(f"    Email: {result['email']}")
                break
            time.sleep(1)  # Small delay between page requests
        
        if not result:
            print(f"  ✗ No trombone teacher found")
            self.failed_universities.append(name)
        
        time.sleep(2)  # Delay between universities
    
    def save_results(self, filename='trombone_teachers.csv'):
        """Save results to CSV file"""
        if self.results:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['university', 'name', 'email', 'university_website', 'faculty_page']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.results)
            
            print(f"\n✓ Results saved to {filename}")
        
        if self.failed_universities:
            with open('failed_universities.txt', 'w', encoding='utf-8') as f:
                for uni in self.failed_universities:
                    f.write(f"{uni}\n")
            print(f"✓ Failed universities saved to failed_universities.txt")
    
    def create_sample_input_files(self):
        """Create sample input files with improved format"""
        
        # CSV with Type column
        csv_content = """University Name,URL,Type
Juilliard School,https://www.juilliard.edu,Conservatory
Curtis Institute of Music,https://www.curtis.edu,Conservatory
Manhattan School of Music,https://www.msmnyc.edu,Conservatory
Eastman School of Music,https://www.esm.rochester.edu,Conservatory
New England Conservatory,https://necmusic.edu,Conservatory
Yale School of Music,https://music.yale.edu,Conservatory
University of Michigan,,University
Northwestern University,https://www.northwestern.edu,University
Indiana University,,University
University of Southern California,,University"""
        
        with open('universities_sample.csv', 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        # JSON format
        json_content = {
            "universities": [
                {"name": "Juilliard School", "url": "https://www.juilliard.edu", "type": "Conservatory"},
                {"name": "Curtis Institute of Music", "url": "https://www.curtis.edu", "type": "Conservatory"},
                {"name": "Manhattan School of Music", "url": "https://www.msmnyc.edu", "type": "Conservatory"},
                {"name": "University of Michigan", "url": null, "type": "University"},
                {"name": "Northwestern University", "url": "https://www.northwestern.edu", "type": "University"}
            ]
        }
        
        with open('universities_sample.json', 'w', encoding='utf-8') as f:
            json.dump(json_content, f, indent=2)
        
        print("✓ Created sample input files with improved format")

# Main script
if __name__ == "__main__":
    import sys
    
    scraper = ImprovedTromboneScraper()
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'trombone_teachers.csv'
    else:
        print("="*60)
        print("IMPROVED TROMBONE TEACHER WEB SCRAPER")
        print("="*60)
        
        if not Path('universities_sample.csv').exists():
            print("\nNo input files found. Creating sample files...")
            scraper.create_sample_input_files()
            print("\nPlease edit the sample files with your university list,")
            print("then run the script again.")
            sys.exit(0)
        
        print("\nAvailable files:")
        for file in Path('.').glob('universities*.csv'):
            print(f"  - {file}")
        for file in Path('.').glob('universities*.json'):
            print(f"  - {file}")
        
        input_file = input("Enter input file (or press Enter for 'universities_sample.csv'): ").strip()
        if not input_file:
            input_file = 'universities_sample.csv'
        
        output_file = input("Enter output file (or press Enter for 'trombone_teachers.csv'): ").strip()
        if not output_file:
            output_file = 'trombone_teachers.csv'
    
    # Load and process universities
    universities = scraper.load_universities_from_file(input_file)
    
    if not universities:
        print("No universities to process. Exiting.")
        sys.exit(1)
    
    print(f"\nStarting to scrape {len(universities)} universities...")
    print("Press Ctrl+C to stop at any time.\n")
    
    try:
        for uni_info in universities:
            scraper.scrape_university(uni_info)
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user.")
    
    scraper.save_results(output_file)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SCRAPING COMPLETE!")
    print(f"✓ Found {len(scraper.results)} trombone teachers")
    print(f"✗ Failed for {len(scraper.failed_universities)} universities")
    
    if scraper.results:
        print(f"\nFound teachers:")
        for result in scraper.results:
            print(f"  • {result['name']} at {result['university']}")
            if result.get('email'):
                print(f"    Email: {result['email']}")