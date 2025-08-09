import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import json
from urllib.parse import urljoin, urlparse, quote
from pathlib import Path

# Optional imports for enhanced functionality
try:
    from googlesearch import search
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    print("Note: googlesearch-python not installed. Auto URL discovery disabled.")

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import ElementNotInteractableException, InvalidElementStateException, TimeoutException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Note: Selenium not installed. JavaScript search disabled.")
    print("      Install with: pip install selenium")

class RobustTromboneScraper:
    def __init__(self, use_selenium=False):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.results = []
        self.failed_universities = []
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.driver = None
        
        if self.use_selenium:
            try:
                chrome_options = Options()
                chrome_options.add_argument('--headless')  # Run in background
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--window-size=1920,1080')  # Set window size
                self.driver = webdriver.Chrome(options=chrome_options)
                print("✓ Selenium initialized for JavaScript search support")
            except Exception as e:
                print(f"Warning: Could not initialize Selenium: {e}")
                self.use_selenium = False
    
    def __del__(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def load_universities_from_file(self, filename):
        """Load universities from CSV file"""
        universities = []
        file_path = Path(filename)
        
        if not file_path.exists():
            print(f"Error: File '{filename}' not found!")
            return universities
        
        try:
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
            
            print(f"✓ Loaded {len(universities)} universities from {filename}")
            return universities
            
        except Exception as e:
            print(f"Error loading file '{filename}': {e}")
            return []
    
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
    
    def search_website(self, base_url, search_terms=None):
        """Try to search the website using common search patterns"""
        if search_terms is None:
            search_terms = ["trombone faculty", "trombone professor", "trombone"]
        
        for search_term in search_terms:
            print(f"  Trying website search for '{search_term}'...")
            
            # Method 1: Try common search URL patterns
            search_urls = [
                f"{base_url}/?s={quote(search_term)}",
                f"{base_url}/search?q={quote(search_term)}",
                f"{base_url}/search?search={quote(search_term)}",
                f"{base_url}/search?query={quote(search_term)}",
                f"{base_url}/search?keyword={quote(search_term)}",
                f"{base_url}/search?keywords={quote(search_term)}",
                f"{base_url}/search/{quote(search_term)}",
                f"{base_url}/search-results?q={quote(search_term)}",
                f"{base_url}/site-search?q={quote(search_term)}"
            ]
            
            for search_url in search_urls:
                try:
                    response = self.session.get(search_url, timeout=10, allow_redirects=True)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        page_text = soup.get_text().lower()
                        
                        # Check if we got search results with relevant content
                        if 'trombone' in page_text and any(word in page_text for word in ['faculty', 'professor', 'music', 'school']):
                            print(f"    ✓ Found search results at: {response.url}")
                            return soup, response.url
                except:
                    continue
        
        # Method 2: Use Selenium if available and no results found
        if self.use_selenium:
            # Try with the best search term for Selenium
            return self.search_with_selenium(base_url, "trombone faculty")
        
        return None, None
    
    def search_with_selenium(self, url, search_term="trombone"):
        """Use Selenium to interact with JavaScript search"""
        if not self.driver:
            return None, None
        
        print(f"    Using Selenium to search...")
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                time.sleep(3)  # Let page load completely
                
                # Try to handle popups/cookies/overlays
                try:
                    # Scroll to top
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    
                    # Try to close common popup/cookie elements
                    popup_selectors = [
                        "button[aria-label*='close' i]",
                        "button[class*='close' i]",
                        "button[id*='close' i]",
                        "a[class*='close' i]",
                        "div[class*='dismiss' i]",
                        "button[class*='accept' i]",  # Cookie accept buttons
                        "button[class*='cookie' i]"
                    ]
                    
                    for selector in popup_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for elem in elements[:2]:  # Only try first 2 to avoid over-clicking
                                if elem.is_displayed() and elem.is_enabled():
                                    elem.click()
                                    time.sleep(1)
                                    break
                        except:
                            pass
                            
                except Exception as e:
                    pass  # Silently continue
                
                # STEP 1: First try to click search icon/button to reveal search box
                print(f"      Looking for search icon to click...")
                search_icon_selectors = [
                    "button[aria-label*='search' i]",
                    "a[aria-label*='search' i]",
                    "button[class*='search-button' i]",
                    "button[class*='search-icon' i]",
                    "a[class*='search-button' i]",
                    "a[class*='search-icon' i]",
                    "button[title*='search' i]",
                    ".search-toggle",
                    "#search-toggle",
                    "button svg[class*='search' i]",  # Search icon inside button
                    "a svg[class*='search' i]",  # Search icon inside link
                    "[class*='search'] button",
                    "[class*='search'] a[href='#']",
                    "button:has(svg[class*='search' i])",  # CSS4 selector
                    "button:has(i[class*='search' i])"  # Font icon
                ]
                
                search_revealed = False
                for selector in search_icon_selectors:
                    try:
                        # Use JavaScript to find elements since CSS4 selectors might not work
                        if ':has(' in selector:
                            # Skip CSS4 selectors for now
                            continue
                            
                        icons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for icon in icons[:3]:  # Try first 3 matches
                            if icon.is_displayed() and icon.is_enabled():
                                try:
                                    # Check if this looks like a search reveal button
                                    parent_class = icon.get_attribute('class') or ''
                                    parent_label = icon.get_attribute('aria-label') or ''
                                    
                                    if 'search' in parent_class.lower() or 'search' in parent_label.lower():
                                        print(f"      Clicking search icon: {selector}")
                                        icon.click()
                                        time.sleep(2)  # Wait for search box to appear
                                        search_revealed = True
                                        break
                                except:
                                    pass
                        
                        if search_revealed:
                            break
                    except:
                        continue
                
                # STEP 2: Now try to find the search input box
                search_selectors = [
                    "input[type='search']:visible",  # Visible search inputs
                    "input[type='text'][placeholder*='search' i]",
                    "input[type='search']",
                    "input[name='s']",
                    "input[name='q']",
                    "input[name='search']",
                    "input[name='query']",
                    "input[placeholder*='earch' i]",
                    "input.search",
                    "input#search",
                    ".search-input input",
                    "#search-input",
                    "input[aria-label*='earch' i]",
                    "input[id*='search' i]",
                    "input[class*='search' i]",
                    "form[role='search'] input[type='text']",
                    "form[class*='search'] input[type='text']"
                ]
                
                search_box = None
                successful_selector = None
                
                for selector in search_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.is_enabled():
                                # Try to click on it first to make it active
                                try:
                                    elem.click()
                                    time.sleep(0.5)
                                except:
                                    pass
                                
                                # Check if we can type in it
                                try:
                                    elem.clear()
                                    elem.send_keys("test")
                                    elem.clear()
                                    search_box = elem
                                    successful_selector = selector
                                    break
                                except (ElementNotInteractableException, InvalidElementStateException):
                                    continue
                        
                        if search_box:
                            break
                            
                    except Exception:
                        continue
                
                if not search_box:
                    # Try JavaScript to find and focus search input
                    try:
                        self.driver.execute_script("""
                            var inputs = document.querySelectorAll('input');
                            for(var i = 0; i < inputs.length; i++) {
                                var input = inputs[i];
                                if(input.type === 'search' || 
                                   input.name === 's' || 
                                   input.name === 'q' ||
                                   input.placeholder.toLowerCase().includes('search')) {
                                    input.focus();
                                    input.click();
                                    return true;
                                }
                            }
                            return false;
                        """)
                        time.sleep(1)
                        # Try to find the focused element
                        search_box = self.driver.switch_to.active_element
                    except:
                        pass
                
                if search_box:
                    print(f"      Found search box using: {successful_selector or 'JavaScript focus'}")
                    
                    # Clear and type search term
                    search_box.clear()
                    search_box.send_keys(search_term)
                    
                    # STEP 3: Find and click search submit button if exists
                    submit_found = False
                    submit_selectors = [
                        "button[type='submit'][class*='search']",
                        "button[class*='search-button']",
                        "button[class*='search-submit']",
                        "input[type='submit'][value*='search' i]",
                        "button[aria-label*='search' i]",
                        ".search-form button[type='submit']",
                        "form[role='search'] button",
                        "form[class*='search'] button[type='submit']"
                    ]
                    
                    for selector in submit_selectors:
                        try:
                            submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for btn in submit_buttons:
                                if btn.is_displayed() and btn.is_enabled():
                                    print(f"      Clicking search submit button")
                                    btn.click()
                                    submit_found = True
                                    break
                            if submit_found:
                                break
                        except:
                            pass
                    
                    # If no button found, just press Enter
                    if not submit_found:
                        print(f"      Pressing Enter to submit search")
                        search_box.send_keys(Keys.RETURN)
                    
                    # Wait for results to load
                    time.sleep(3)
                    
                    # Check if results loaded
                    try:
                        WebDriverWait(self.driver, 5).until(
                            lambda d: search_term.lower() in d.page_source.lower()
                        )
                    except TimeoutException:
                        print(f"      Warning: Search may not have returned results")
                    
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    current_url = self.driver.current_url
                    print(f"      ✓ Search completed via Selenium")
                    return soup, current_url
                else:
                    print(f"      Attempt {attempt + 1}: Could not find search box")
                    if attempt < max_retries - 1:
                        print(f"      Retrying...")
                        
            except ElementNotInteractableException as e:
                print(f"      Search box found but not interactable (attempt {attempt + 1})")
                print(f"      This often means the search is hidden or requires clicking a button first")
                
                # Try to find and click a search button/icon that might reveal the search box
                try:
                    search_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                        "button[aria-label*='search' i], a[href*='search'], button[class*='search' i]")
                    for btn in search_buttons[:3]:
                        if btn.is_displayed():
                            btn.click()
                            time.sleep(2)
                            break
                except:
                    pass
                    
            except InvalidElementStateException as e:
                print(f"      Search box in invalid state (attempt {attempt + 1})")
                print(f"      The element exists but isn't ready for input")
                
            except Exception as e:
                print(f"      Selenium error (attempt {attempt + 1}): {type(e).__name__}: {str(e)[:100]}")
        
        print(f"      Could not complete search with Selenium after {max_retries} attempts")
        return None, None
    
    def extract_emails(self, text):
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return [e for e in emails if not any(x in e.lower() for x in ['example', 'domain', 'email', 'your', 'info@', 'admin@', 'webmaster@'])]
    
    def is_valid_name(self, text):
        """Check if text is likely a person's name"""
        if not text or len(text) < 5 or len(text) > 50:
            return False
        
        parts = text.split()
        if len(parts) < 2 or len(parts) > 5:
            return False
        
        # Expanded list of non-names
        non_name_words = {
            'faculty', 'staff', 'department', 'school', 'college', 'university',
            'music', 'brass', 'professor', 'instructor', 'lecturer',
            'search', 'filter', 'results', 'loading', 'welcome', 'percussion',
            'undergraduate', 'graduate', 'diploma', 'degree', 'bachelor', 'master',
            'performance', 'ensemble', 'orchestra', 'symphony', 'philharmonic',
            'endowed', 'chair', 'position', 'program', 'studio', 'class',
            'concert', 'recital', 'audition', 'admission', 'apply', 'application',
            'curriculum', 'course', 'lesson', 'workshop', 'masterclass', 'seminar',
            'summer', 'institute', 'spotlight', 'main', 'navigation', 'level'
        }
        
        # Don't reject "Saxophone Jazz" style - check individual words
        text_lower = text.lower()
        
        # Check if ALL words are non-names (reject things like "Main Navigation")
        all_non_names = all(part.lower() in non_name_words for part in parts)
        if all_non_names:
            return False
        
        # Check for instrument names that shouldn't be part of a person's name
        instrument_words = {'saxophone', 'trumpet', 'tuba', 'horn', 'jazz', 'tenor', 'alto', 'soprano', 'baritone', 'bass'}
        for word in instrument_words:
            if word in text_lower:
                return False
        
        # Must have at least one uppercase word (for last names)
        has_proper_name = any(p[0].isupper() for p in parts if p)
        
        # Check for common name patterns (First Last, First M. Last, etc.)
        name_pattern = r'^[A-Z][a-z]+(\s+[A-Z]\.?)?\s+[A-Z][a-z]+(-[A-Z][a-z]+)?$'
        if re.match(name_pattern, text):
            return True
        
        return has_proper_name and len(parts) >= 2
    
    def extract_trombone_faculty(self, soup, page_text):
        """Extract trombone faculty from search results or faculty page"""
        results = []
        
        # Strategy 1: Extract from search result headings and descriptions
        # Look for patterns like "Peter Ellefson: Current: Faculty: Jacobs School of Music"
        result_entries = soup.find_all(['div', 'article', 'li', 'section', 'h3', 'h4'])
        
        for entry in result_entries:
            entry_text = entry.get_text()
            entry_lower = entry_text.lower()
            
            # Check if this entry mentions trombone and faculty/professor
            if 'trombone' in entry_lower and any(term in entry_lower for term in ['faculty', 'professor', 'music']):
                # Try to extract name from the beginning of the entry
                # Often formatted as "Name: Title: Department"
                lines = entry_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and ':' in line:
                        # Get the first part before the colon
                        potential_name = line.split(':')[0].strip()
                    else:
                        potential_name = line
                    
                    # Clean and validate the name
                    potential_name = re.sub(r'\s+', ' ', potential_name)  # Normalize whitespace
                    potential_name = potential_name.strip()
                    
                    if self.is_valid_name(potential_name) and len(potential_name) > 5:
                        # Look for email in the entry
                        emails = self.extract_emails(entry_text)
                        
                        # Make sure we're not duplicating
                        if not any(r['name'] == potential_name for r in results):
                            results.append({
                                'name': potential_name,
                                'email': emails[0] if emails else None
                            })
                            break  # Found a name in this entry, move to next
        
        # Strategy 1b: Look for linked names in search results
        # Find all links in the page that might be faculty names
        all_links = soup.find_all('a')
        for link in all_links:
            link_text = link.get_text().strip()
            # Check if the link's parent or nearby text mentions trombone
            parent = link.parent
            if parent:
                parent_text = parent.get_text().lower()
                if 'trombone' in parent_text and self.is_valid_name(link_text):
                    if not any(r['name'] == link_text for r in results):
                        results.append({
                            'name': link_text,
                            'email': None
                        })
        
        # Strategy 2: Look for faculty cards/profiles containing "trombone"
        faculty_containers = soup.find_all(['div', 'article', 'li', 'section'], 
                                          class_=re.compile('faculty|staff|people|profile|member|person|instructor', re.I))
        
        for container in faculty_containers:
            container_text = container.get_text()
            if 'trombone' in container_text.lower():
                # Find name (usually in heading or link)
                name_elems = container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'a', 'strong'])
                for name_elem in name_elems:
                    name = name_elem.get_text().strip()
                    if self.is_valid_name(name):
                        emails = self.extract_emails(container_text)
                        if not any(r['name'] == name for r in results):
                            results.append({
                                'name': name,
                                'email': emails[0] if emails else None
                            })
                        break  # Only take first valid name per container
        
        # Strategy 3: Look for specific patterns in search results
        # Pattern: "Name | Institution" where text contains trombone and professor
        name_institution_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*\|\s*[^|]+'
        matches = re.findall(name_institution_pattern, page_text)
        for match in matches:
            # Check if this match is near "trombone" and "professor"
            match_index = page_text.find(match)
            context = page_text[max(0, match_index-100):match_index+300].lower()
            if 'trombone' in context and ('professor' in context or 'faculty' in context):
                if self.is_valid_name(match):
                    emails = self.extract_emails(context)
                    if not any(r['name'] == match for r in results):
                        results.append({
                            'name': match,
                            'email': emails[0] if emails else None
                        })
        
        # Strategy 4: Pattern matching for various name formats
        patterns = [
            # "Name, bass trombone" or "Name, trombone"
            r'([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+(?:-[A-Z][a-z]+)?),?\s*(?:bass\s+)?trombone',
            # "trombone: Name" or "bass trombone: Name"
            r'(?:bass\s+)?[Tt]rombone\s*(?:–|-|:|,)\s*([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+(?:-[A-Z][a-z]+)?)',
            # "Name (trombone)" or "Name (bass trombone)"
            r'([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s*\((?:bass\s+)?[Tt]rombone\)',
            # "Name Trombone Faculty" or "Name Professor of Trombone"
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s+(?:[Tt]rombone\s+[Ff]aculty|[Pp]rofessor\s+of\s+[Tt]rombone)',
            # For entries like "Dylan Halliday, bass trombone"
            r'([A-Z][a-z]+\s+[A-Z][a-z]+),\s*bass\s+trombone',
            # For entries like "Andrew Ng, bass trombone"
            r'([A-Z][a-z]+\s+[A-Z][a-z]+),\s*(?:bass\s+)?trombone\s*[^.|;]',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                if self.is_valid_name(match):
                    # Find email near this name
                    name_index = page_text.find(match)
                    context = page_text[max(0, name_index-200):name_index+200]
                    emails = self.extract_emails(context)
                    
                    if not any(r['name'] == match for r in results):
                        results.append({
                            'name': match,
                            'email': emails[0] if emails else None
                        })
        
        # Remove duplicates and invalid names
        seen_names = set()
        unique_results = []
        for result in results:
            name = result['name']
            # Final validation
            if name not in seen_names and self.is_valid_name(name):
                seen_names.add(name)
                unique_results.append(result)
        
        return unique_results
    
    def find_faculty_pages(self, base_url, is_music_school=False):
        """Find faculty pages with multiple strategies"""
        found_pages = []
        
        # Strategy 1: Direct faculty page URLs
        if is_music_school:
            paths = ['/faculty', '/people', '/faculty-staff', '/directory', '/brass']
        else:
            paths = ['/music/faculty', '/music/people', '/school-of-music/faculty', '/music/directory']
        
        for path in paths:
            try:
                url = urljoin(base_url, path)
                response = self.session.get(url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_text = soup.get_text().lower()
                    
                    if any(word in page_text for word in ['faculty', 'people', 'staff', 'instructor', 'professor']):
                        found_pages.append(response.url)
                        if 'trombone' in page_text or 'brass' in page_text:
                            return [response.url]  # Priority page
            except:
                continue
        
        # Strategy 2: Search homepage for faculty links
        if not found_pages:
            try:
                response = self.session.get(base_url, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find all links that might lead to faculty
                links = soup.find_all('a', href=True)
                for link in links:
                    link_text = link.get_text().lower()
                    link_href = link['href'].lower()
                    
                    if any(word in link_text or word in link_href for word in ['faculty', 'people', 'directory', 'staff']):
                        full_url = urljoin(base_url, link['href'])
                        if full_url not in found_pages:
                            found_pages.append(full_url)
                            if len(found_pages) >= 3:
                                break
            except:
                pass
        
        return found_pages[:3]
    
    def scrape_university(self, uni_info):
        """Main method to scrape a university website"""
        name = uni_info['name']
        base_url = uni_info['url']
        is_music_school = uni_info.get('is_music_school', False)
        
        print(f"\n{'='*60}")
        print(f"Scraping {name}...")
        if is_music_school:
            print(f"  (Music Conservatory)")
        
        # Find URL if not provided
        if not base_url:
            print(f"  Looking up URL for {name}...")
            base_url = self.find_university_url(name)
            if not base_url:
                print(f"  ✗ Could not find URL")
                self.failed_universities.append(name)
                return
            print(f"  ✓ Found: {base_url}")
        
        # Strategy 1: Try website search with multiple search terms
        search_soup, search_url = self.search_website(base_url)
        
        if search_soup:
            results = self.extract_trombone_faculty(search_soup, search_soup.get_text())
            if results:
                # Take up to 3 results from search (might find multiple faculty)
                for result in results[:3]:
                    # Check if we already have this person
                    if not any(r['university'] == name and r['name'] == result['name'] for r in self.results):
                        result['university'] = name
                        result['university_website'] = base_url
                        result['source'] = 'Website Search'
                        self.results.append(result)
                        print(f"  ✓ Found via search: {result['name']}")
                        if result.get('email'):
                            print(f"    Email: {result['email']}")
                
                if results:  # If we found anyone, consider it successful
                    return
        
        # Strategy 2: Look for faculty pages
        print(f"  Looking for faculty pages...")
        faculty_pages = self.find_faculty_pages(base_url, is_music_school)
        
        if faculty_pages:
            for page_url in faculty_pages:
                try:
                    response = self.session.get(page_url, timeout=15)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_text = soup.get_text()
                    
                    if 'trombone' in page_text.lower():
                        print(f"    Found 'trombone' at: {page_url}")
                        results = self.extract_trombone_faculty(soup, page_text)
                        if results:
                            result = results[0]
                            result['university'] = name
                            result['university_website'] = base_url
                            result['source'] = 'Faculty Page'
                            self.results.append(result)
                            print(f"  ✓ Found: {result['name']}")
                            if result.get('email'):
                                print(f"    Email: {result['email']}")
                            return
                except Exception as e:
                    print(f"    Error accessing {page_url}: {e}")
                
                time.sleep(1)
        
        print(f"  ✗ No trombone teacher found")
        self.failed_universities.append(name)
        
        time.sleep(2)  # Delay between universities
    
    def save_results(self, filename='trombone_teachers.csv'):
        """Save results to CSV file"""
        if self.results:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['university', 'name', 'email', 'university_website', 'source']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.results)
            print(f"\n✓ Results saved to {filename}")
        
        if self.failed_universities:
            with open('failed_universities.txt', 'w', encoding='utf-8') as f:
                for uni in self.failed_universities:
                    f.write(f"{uni}\n")
            print(f"✓ Failed universities saved to failed_universities.txt")
    
    def create_sample_input_file(self):
        """Create a sample input file"""
        csv_content = """University Name,URL,Type
Juilliard School,https://www.juilliard.edu,Conservatory
Curtis Institute of Music,https://www.curtis.edu,Conservatory
Manhattan School of Music,https://www.msmnyc.edu,Conservatory
Eastman School of Music,https://www.esm.rochester.edu,Conservatory
New England Conservatory,https://necmusic.edu,Conservatory
San Francisco Conservatory,https://sfcm.edu,Conservatory
University of Michigan,,University
Northwestern University,https://www.northwestern.edu,University
Indiana University,,University
Yale School of Music,https://music.yale.edu,Conservatory"""
        
        with open('universities_sample.csv', 'w', encoding='utf-8') as f:
            f.write(csv_content)
        print("✓ Created universities_sample.csv")

# Main script
if __name__ == "__main__":
    import sys
    
    # Check for --selenium flag
    use_selenium = '--selenium' in sys.argv
    if use_selenium:
        sys.argv.remove('--selenium')
    
    scraper = RobustTromboneScraper(use_selenium=use_selenium)
    
    # Get input/output files
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'trombone_teachers.csv'
    else:
        print("="*60)
        print("ROBUST TROMBONE TEACHER WEB SCRAPER")
        print("="*60)
        
        if not Path('universities_sample.csv').exists():
            print("\nCreating sample input file...")
            scraper.create_sample_input_file()
        
        print("\nUsage:")
        print("  python robust_scraper.py [input.csv] [output.csv]")
        print("  python robust_scraper.py --selenium [input.csv]  # For JavaScript sites")
        print("")
        
        input_file = input("Enter input file (default: universities_sample.csv): ").strip()
        if not input_file:
            input_file = 'universities_sample.csv'
        
        output_file = input("Enter output file (default: trombone_teachers.csv): ").strip()
        if not output_file:
            output_file = 'trombone_teachers.csv'
    
    # Load and process
    universities = scraper.load_universities_from_file(input_file)
    
    if not universities:
        print("No universities to process.")
        sys.exit(1)
    
    print(f"\nProcessing {len(universities)} universities...")
    print("Press Ctrl+C to stop.\n")
    
    try:
        for uni_info in universities:
            scraper.scrape_university(uni_info)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    
    scraper.save_results(output_file)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"COMPLETE!")
    print(f"✓ Found {len(scraper.results)} trombone teachers")
    print(f"✗ Failed for {len(scraper.failed_universities)} universities")
    
    if scraper.results:
        print(f"\nResults:")
        for result in scraper.results:
            print(f"  • {result['name']} at {result['university']}")
            if result.get('email'):
                print(f"    {result['email']}")
