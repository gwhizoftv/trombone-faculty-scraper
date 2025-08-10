import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import json
from urllib.parse import urljoin, urlparse
from pathlib import Path
try:
    from googlesearch import search  # You'll need: pip install googlesearch-python
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    print("Warning: googlesearch-python not installed. Auto URL discovery disabled.")

class EnhancedTromboneScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
                # CSV format: University Name, URL (optional)
                with open(filename, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    # Skip header if it exists
                    first_row = next(reader, None)
                    if first_row and 'university' in first_row[0].lower():
                        pass  # This was a header
                    else:
                        # Not a header, process it
                        if first_row:
                            if len(first_row) >= 2 and first_row[1].strip():
                                universities.append((first_row[0].strip(), first_row[1].strip()))
                            else:
                                universities.append((first_row[0].strip(), None))
                    
                    # Process remaining rows
                    for row in reader:
                        if row:  # Skip empty rows
                            if len(row) >= 2 and row[1].strip():
                                universities.append((row[0].strip(), row[1].strip()))
                            else:
                                universities.append((row[0].strip(), None))
            
            elif file_extension == '.json':
                # JSON format: {"universities": [{"name": "...", "url": "..."}, ...]}
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for uni in data.get('universities', []):
                        if isinstance(uni, dict):
                            universities.append((uni.get('name'), uni.get('url')))
                        elif isinstance(uni, str):
                            universities.append((uni, None))
            
            elif file_extension == '.txt':
                # TXT format: One university per line, optionally with URL after comma or tab
                with open(filename, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):  # Skip empty lines and comments
                            if '\t' in line:
                                parts = line.split('\t', 1)
                            elif ',' in line:
                                parts = line.split(',', 1)
                            else:
                                parts = [line]
                            
                            if len(parts) >= 2 and parts[1].strip():
                                universities.append((parts[0].strip(), parts[1].strip()))
                            else:
                                universities.append((parts[0].strip(), None))
            
            print(f"✓ Loaded {len(universities)} universities from {filename}")
            return universities
            
        except Exception as e:
            print(f"Error loading file '{filename}': {e}")
            return universities
    
    def find_university_url(self, university_name):
        """Use Google to find the university's main website"""
        if not GOOGLE_SEARCH_AVAILABLE:
            print(f"  Cannot auto-find URL for {university_name} (googlesearch not installed)")
            return None
            
        try:
            # Search for the university
            query = f"{university_name} official website"
            for url in search(query, num_results=3):
                if '.edu' in url or '.ac.' in url:  # Educational domains
                    return url
        except Exception as e:
            print(f"  Could not find URL for {university_name}: {e}")
        return None
    
    def extract_emails(self, text):
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(email_pattern, text)
    
    def smart_department_search(self, base_url):
        """Enhanced search for music department with multiple strategies"""
        
        # Strategy 1: Try common music department URLs
        common_paths = [
            '/music',
            '/music/',
            '/som',  # School of Music
            '/musicdepartment',
            '/music-department',
            '/department-of-music',
            '/school-of-music',
            '/college-of-music',
            '/conservatory',
            '/music/faculty',
            '/music/people',
            '/music/staff',
            '/music/brass',
            '/music/faculty/brass',
            '/academics/music',
            '/departments/music',
            '/programs/music',
            '/cfa/music',  # College of Fine Arts
            '/arts/music',
            '/performing-arts/music'
        ]
        
        print(f"  Searching for music department...")
        for path in common_paths:
            try:
                url = urljoin(base_url, path)
                response = self.session.get(url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    # Verify it's actually a music page
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_text = soup.get_text().lower()
                    if 'music' in page_text or 'faculty' in page_text:
                        print(f"  ✓ Found music department at: {response.url}")
                        return response.url
            except:
                continue
        
        # Strategy 2: Search the homepage for music department links
        try:
            print(f"  Searching homepage for music links...")
            response = self.session.get(base_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for links containing "music"
            music_links = soup.find_all('a', href=True)
            for link in music_links:
                link_text = link.get_text().lower()
                link_href = link['href'].lower()
                if 'school of music' in link_text or 'music department' in link_text or '/music' in link_href:
                    full_url = urljoin(base_url, link['href'])
                    print(f"  ✓ Found music link: {full_url}")
                    return full_url
        except:
            pass
        
        return None
    
    def find_trombone_faculty(self, url, depth=0, visited=None):
        """Recursively search for trombone faculty (with depth limit)"""
        if depth > 2:  # Don't go too deep
            return None
        
        if visited is None:
            visited = set()
        
        if url in visited:
            return None
        
        visited.add(url)
        
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Check if this page mentions trombone
            if 'trombone' in page_text:
                print(f"    Found 'trombone' mention at: {url}")
                
                # Look for faculty information near "trombone"
                all_text = soup.get_text()
                
                # Find the position of "trombone" in the text
                trombone_positions = [m.start() for m in re.finditer(r'trombone', all_text, re.I)]
                
                for pos in trombone_positions:
                    # Extract context around "trombone" (500 chars before and after)
                    context = all_text[max(0, pos-500):pos+500]
                    
                    # Look for names (capitalized words)
                    name_pattern = r'\b([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
                    potential_names = re.findall(name_pattern, context)
                    
                    # Look for emails in the context
                    emails = self.extract_emails(context)
                    
                    # Filter out common non-names
                    non_names = ['School Music', 'University College', 'Department Music', 
                                'Music Department', 'Associate Professor', 'Assistant Professor',
                                'Music Building', 'Concert Hall', 'Bachelor Music', 'Master Music']
                    
                    for name in potential_names:
                        if name not in non_names and len(name) > 5:
                            return {
                                'name': name,
                                'email': emails[0] if emails else None,
                                'source_url': url,
                                'context': context[:200]  # Save some context
                            }
            
            # If not found on this page, check linked pages (faculty, people, brass pages)
            if depth == 0:
                relevant_links = soup.find_all('a', href=True)
                for link in relevant_links:
                    link_text = link.get_text().lower()
                    link_href = link['href'].lower()
                    
                    # Check if this might be a relevant faculty/brass page
                    if any(keyword in link_text or keyword in link_href 
                          for keyword in ['faculty', 'people', 'staff', 'brass', 'trombone', 'wind', 'instrumental']):
                        full_url = urljoin(url, link['href'])
                        if full_url != url:  # Don't revisit the same page
                            result = self.find_trombone_faculty(full_url, depth + 1, visited)
                            if result:
                                return result
                            time.sleep(0.5)  # Small delay between requests
            
        except Exception as e:
            print(f"    Error accessing {url}: {e}")
        
        return None
    
    def scrape_university(self, university_name, base_url=None):
        """Main method to scrape a university website"""
        print(f"\n{'='*60}")
        print(f"Scraping {university_name}...")
        
        # Find the university URL if not provided
        if not base_url:
            print(f"  Looking up URL for {university_name}...")
            base_url = self.find_university_url(university_name)
            if not base_url:
                print(f"  ✗ Could not find URL for {university_name}")
                self.failed_universities.append(university_name)
                return
            print(f"  ✓ Found: {base_url}")
        
        # Find music department
        music_dept_url = self.smart_department_search(base_url)
        
        if music_dept_url:
            # Search for trombone faculty
            print(f"  Searching for trombone faculty...")
            result = self.find_trombone_faculty(music_dept_url)
            
            if result:
                result['university'] = university_name
                result['university_website'] = base_url
                result['music_dept_url'] = music_dept_url
                self.results.append(result)
                print(f"  ✓ Found trombone teacher: {result['name']}")
                if result['email']:
                    print(f"    Email: {result['email']}")
            else:
                print(f"  ✗ No trombone teacher found")
                self.failed_universities.append(university_name)
        else:
            print(f"  ✗ Could not find music department")
            self.failed_universities.append(university_name)
        
        # Be respectful - add delay between universities
        time.sleep(2)
    
    def save_results(self, filename='trombone_teachers.csv'):
        """Save results to CSV file"""
        if self.results:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['university', 'name', 'email', 'university_website', 
                            'music_dept_url', 'source_url']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.results)
            
            print(f"\n✓ Results saved to {filename}")
        
        # Also save failed universities for reference
        if self.failed_universities:
            with open('failed_universities.txt', 'w', encoding='utf-8') as f:
                for uni in self.failed_universities:
                    f.write(f"{uni}\n")
            print(f"✓ Failed universities saved to failed_universities.txt")
    
    def create_sample_input_files(self):
        """Create sample input files to show the format"""
        
        # Create sample CSV
        csv_content = """University Name,URL
Juilliard School,https://www.juilliard.edu
Berklee College of Music,
University of Michigan,https://www.umich.edu
Indiana University,
Eastman School of Music,
Yale School of Music,https://www.yale.edu
Northwestern University Bienen School of Music,
Manhattan School of Music,
New England Conservatory,
Curtis Institute of Music,https://www.curtis.edu"""
        
        with open('universities_sample.csv', 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        # Create sample TXT
        txt_content = """# List of universities to scrape
# Format: University Name, URL (optional)
# Lines starting with # are comments

Juilliard School, https://www.juilliard.edu
Berklee College of Music
University of Michigan, https://www.umich.edu
Indiana University
Eastman School of Music
Yale School of Music
Northwestern University
Manhattan School of Music
New England Conservatory
Curtis Institute of Music"""
        
        with open('universities_sample.txt', 'w', encoding='utf-8') as f:
            f.write(txt_content)
        
        # Create sample JSON
        json_content = {
            "universities": [
                {"name": "Juilliard School", "url": "https://www.juilliard.edu"},
                {"name": "Berklee College of Music", "url": None},
                {"name": "University of Michigan", "url": "https://www.umich.edu"},
                {"name": "Indiana University", "url": None},
                {"name": "Eastman School of Music", "url": None}
            ]
        }
        
        with open('universities_sample.json', 'w', encoding='utf-8') as f:
            json.dump(json_content, f, indent=2)
        
        print("✓ Created sample input files:")
        print("  - universities_sample.csv")
        print("  - universities_sample.txt")
        print("  - universities_sample.json")

# Main script
if __name__ == "__main__":
    import sys
    
    scraper = EnhancedTromboneScraper()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        # Use file provided as command line argument
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'trombone_teachers.csv'
    else:
        # Interactive mode
        print("="*60)
        print("TROMBONE TEACHER WEB SCRAPER")
        print("="*60)
        
        # Check if sample files exist, if not create them
        if not Path('universities_sample.csv').exists():
            print("\nNo input files found. Creating sample files...")
            scraper.create_sample_input_files()
            print("\nPlease edit one of the sample files with your university list,")
            print("then run the script again with:")
            print("  python script.py universities_sample.csv")
            sys.exit(0)
        
        # Ask user for input file
        print("\nAvailable sample files:")
        for ext in ['csv', 'txt', 'json']:
            file = f'universities_sample.{ext}'
            if Path(file).exists():
                print(f"  - {file}")
        
        input_file = input("Enter the input file name (or press Enter for 'universities_sample.csv'): ").strip()
        if not input_file:
            input_file = 'universities_sample.csv'
        
        output_file = input("Enter output file name (or press Enter for 'trombone_teachers.csv'): ").strip()
        if not output_file:
            output_file = 'trombone_teachers.csv'
    
    # Load universities from file
    universities = scraper.load_universities_from_file(input_file)
    
    if not universities:
        print("No universities to process. Exiting.")
        sys.exit(1)
    
    # Process each university
    print(f"\nStarting to scrape {len(universities)} universities...")
    print("This may take a while. Press Ctrl+C to stop at any time.\n")
    
    try:
        for name, url in universities:
            scraper.scrape_university(name, url)
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user.")
    
    # Save results
    scraper.save_results(output_file)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"SCRAPING COMPLETE!")
    print(f"✓ Found {len(scraper.results)} trombone teachers")
    print(f"✗ Failed to find info for {len(scraper.failed_universities)} universities")
    
    if scraper.results:
        print(f"\nResults saved to: {output_file}")
        print("\nFound teachers:")
        for result in scraper.results:
            print(f"  • {result['name']} at {result['university']}")
            if result['email']:
                print(f"    Email: {result['email']}")
