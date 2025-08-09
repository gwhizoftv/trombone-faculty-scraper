import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from urllib.parse import urljoin, urlparse

class UniversityTromboneScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.results = []
    
    def extract_emails(self, text):
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(email_pattern, text)
    
    def search_music_department(self, base_url):
        """Search for music department pages"""
        common_paths = [
            '/music',
            '/music-department',
            '/school-of-music',
            '/college-of-music',
            '/music/faculty',
            '/music/people',
            '/music/staff',
            '/music/brass',
            '/music/faculty/brass'
        ]
        
        for path in common_paths:
            try:
                url = urljoin(base_url, path)
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    return url
            except:
                continue
        return None
    
    def scrape_faculty_page(self, url):
        """Scrape a faculty/department page for trombone teachers"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Convert to lowercase for searching
            page_text = soup.get_text().lower()
            
            # Look for trombone-related keywords
            if 'trombone' in page_text:
                # Try to find faculty cards or sections
                faculty_sections = soup.find_all(['div', 'article', 'section'], 
                                                class_=re.compile('faculty|staff|people|profile'))
                
                for section in faculty_sections:
                    section_text = section.get_text()
                    if 'trombone' in section_text.lower():
                        # Extract name (usually in h2, h3, h4, or strong tags)
                        name = None
                        name_tags = section.find_all(['h2', 'h3', 'h4', 'strong'])
                        for tag in name_tags:
                            potential_name = tag.get_text().strip()
                            if len(potential_name) > 3 and len(potential_name) < 50:
                                name = potential_name
                                break
                        
                        # Extract email
                        emails = self.extract_emails(section_text)
                        email = emails[0] if emails else None
                        
                        if name:
                            return {
                                'name': name,
                                'email': email,
                                'department_url': url
                            }
            
            # Alternative: look for links with 'trombone' in them
            trombone_links = soup.find_all('a', string=re.compile('trombone', re.I))
            for link in trombone_links:
                if link.get('href'):
                    faculty_url = urljoin(url, link['href'])
                    return self.scrape_individual_page(faculty_url)
                    
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        
        return None
    
    def scrape_individual_page(self, url):
        """Scrape an individual faculty member's page"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract name from title or h1
            name = None
            title_tag = soup.find('h1')
            if title_tag:
                name = title_tag.get_text().strip()
            
            # Extract email
            page_text = soup.get_text()
            emails = self.extract_emails(page_text)
            email = emails[0] if emails else None
            
            return {
                'name': name,
                'email': email,
                'profile_url': url
            }
            
        except Exception as e:
            print(f"Error scraping individual page {url}: {e}")
        
        return None
    
    def scrape_university(self, university_name, base_url):
        """Main method to scrape a university website"""
        print(f"Scraping {university_name}...")
        
        # Find music department
        music_dept_url = self.search_music_department(base_url)
        
        if music_dept_url:
            print(f"Found music department: {music_dept_url}")
            
            # Try to find trombone faculty
            result = self.scrape_faculty_page(music_dept_url)
            
            if result:
                result['university'] = university_name
                result['university_website'] = base_url
                self.results.append(result)
                print(f"Found trombone teacher: {result['name']}")
            else:
                print(f"No trombone teacher found at {university_name}")
        else:
            print(f"Could not find music department at {university_name}")
        
        # Be respectful - add delay between requests
        time.sleep(2)
    
    def save_results(self, filename='trombone_teachers.csv'):
        """Save results to CSV file"""
        if self.results:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['university', 'name', 'email', 'university_website', 'department_url', 'profile_url']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in self.results:
                    # Ensure all fields exist
                    for field in fieldnames:
                        if field not in result:
                            result[field] = ''
                    writer.writerow(result)
            
            print(f"\nResults saved to {filename}")
        else:
            print("\nNo results to save")

# Example usage
if __name__ == "__main__":
    scraper = UniversityTromboneScraper()
    
    # List of universities to scrape
    # Add universities in format: ('University Name', 'https://www.university.edu')
    universities = [
        ('Example University', 'https://www.example.edu'),
        # Add more universities here
    ]
    
    # Scrape each university
    for name, url in universities:
        scraper.scrape_university(name, url)
    
    # Save results
    scraper.save_results()
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Scraping complete!")
    print(f"Found {len(scraper.results)} trombone teachers")
    for result in scraper.results:
        print(f"- {result['name']} at {result['university']}")
