#!/usr/bin/env python3
"""
Direct Playwright scraper for trombone faculty
Uses Playwright directly to handle JavaScript-heavy sites
"""

import asyncio
import csv
import re
from pathlib import Path
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser

class TromboneFacultyScraper:
    def __init__(self):
        self.results = []
        self.failed_universities = []
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def setup(self):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
    
    async def cleanup(self):
        """Clean up Playwright resources"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return [e for e in emails if not any(x in e.lower() for x in 
                ['example', 'domain', 'email', 'your', 'info@', 'admin@', 'webmaster@'])]
    
    def is_valid_name(self, text: str) -> bool:
        """Check if text is likely a person's name"""
        if not text or len(text) < 5 or len(text) > 50:
            return False
        
        parts = text.split()
        if len(parts) < 2 or len(parts) > 5:
            return False
        
        non_name_words = {
            'faculty', 'staff', 'department', 'school', 'college', 'university',
            'music', 'brass', 'professor', 'instructor', 'lecturer', 'trombone',
            'search', 'filter', 'results', 'loading', 'welcome', 'percussion',
            'undergraduate', 'graduate', 'diploma', 'degree', 'bachelor', 'master'
        }
        
        all_non_names = all(part.lower() in non_name_words for part in parts)
        if all_non_names:
            return False
        
        has_proper_name = any(p[0].isupper() for p in parts if p)
        return has_proper_name and len(parts) >= 2
    
    def extract_faculty(self, text: str) -> List[Dict]:
        """Extract faculty from page text"""
        faculty = []
        
        # Pattern matching for various formats
        patterns = [
            # Larry Isaacson, Norman Bolter format from Berklee
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\|\s*[^|]*at Berklee',
            # Dylan Halliday, bass trombone format
            r'([A-Z][a-z]+ [A-Z][a-z]+),\s*(?:bass\s+)?trombone',
            # Peter Ellefson: Current: Faculty format
            r'([A-Z][a-z]+ [A-Z][a-z]+):\s*Current:\s*Faculty',
            # Professor of Trombone format
            r'([A-Z][a-z]+ [A-Z][a-z]+).*?[Pp]rofessor of [Tt]rombone',
            # Simple name before trombone
            r'([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+).*?trombone'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if self.is_valid_name(match):
                    # Find email near this name
                    name_index = text.find(match)
                    if name_index != -1:
                        context = text[max(0, name_index-300):name_index+300]
                        emails = self.extract_emails(context)
                        
                        if not any(f['name'] == match for f in faculty):
                            faculty.append({
                                'name': match,
                                'email': emails[0] if emails else None
                            })
        
        return faculty
    
    async def search_on_site(self, search_term: str) -> bool:
        """Try to search on the current page"""
        # Try different search strategies
        
        # Strategy 1: Click search button/icon first
        search_button_selectors = [
            'button[aria-label*="search" i]',
            'a[aria-label*="search" i]',
            'button.search',
            '#search-button',
            '.search-toggle',
            '[class*="search-icon"]',
            '[class*="search-button"]'
        ]
        
        for selector in search_button_selectors:
            try:
                button = await self.page.wait_for_selector(selector, timeout=2000)
                if button:
                    await button.click()
                    await self.page.wait_for_timeout(1000)
                    break
            except:
                continue
        
        # Strategy 2: Find and fill search input
        search_input_selectors = [
            'input[type="search"]',
            'input[name="s"]',
            'input[name="q"]',
            'input[name="search"]',
            'input[placeholder*="search" i]',
            'input#search',
            '.search-input input',
            'input[aria-label*="search" i]'
        ]
        
        for selector in search_input_selectors:
            try:
                search_input = await self.page.wait_for_selector(selector, timeout=2000)
                if search_input:
                    await search_input.fill(search_term)
                    await search_input.press('Enter')
                    await self.page.wait_for_load_state('networkidle', timeout=5000)
                    return True
            except:
                continue
        
        return False
    
    async def scrape_university(self, uni_info: Dict):
        """Scrape a single university"""
        name = uni_info['name']
        url = uni_info.get('url')
        
        print(f"\n{'='*60}")
        print(f"Scraping {name}...")
        
        if not url:
            print(f"  ✗ No URL provided")
            self.failed_universities.append(name)
            return
        
        try:
            # Navigate to the university website
            await self.page.goto(url, wait_until='domcontentloaded', timeout=15000)
            await self.page.wait_for_timeout(1000)
            
            # Try to search for trombone faculty
            print(f"  Searching for 'trombone faculty'...")
            search_success = await self.search_on_site("trombone faculty")
            
            if search_success:
                await self.page.wait_for_timeout(3000)
            
            # Get page content
            content = await self.page.content()
            text = await self.page.inner_text('body')
            
            # Extract faculty
            if 'trombone' in text.lower():
                faculty = self.extract_faculty(text)
                if faculty:
                    for f in faculty[:3]:  # Take up to 3 results
                        f['university'] = name
                        f['university_website'] = url
                        f['source'] = 'Playwright Scrape'
                        self.results.append(f)
                        print(f"  ✓ Found: {f['name']}")
                        if f.get('email'):
                            print(f"    Email: {f['email']}")
                    return
            
            # Try faculty page URLs
            faculty_paths = ['/music/faculty', '/faculty', '/people', '/music/people']
            for path in faculty_paths:
                try:
                    full_url = url.rstrip('/') + path
                    print(f"  Trying {path}...")
                    await self.page.goto(full_url, wait_until='domcontentloaded', timeout=10000)
                    text = await self.page.inner_text('body')
                    
                    if 'trombone' in text.lower():
                        faculty = self.extract_faculty(text)
                        if faculty:
                            f = faculty[0]
                            f['university'] = name
                            f['university_website'] = url
                            f['source'] = 'Faculty Page'
                            self.results.append(f)
                            print(f"  ✓ Found: {f['name']}")
                            if f.get('email'):
                                print(f"    Email: {f['email']}")
                            return
                except:
                    continue
            
            print(f"  ✗ No trombone faculty found")
            self.failed_universities.append(name)
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
            self.failed_universities.append(name)
    
    def load_universities(self, filename: str) -> List[Dict]:
        """Load universities from CSV"""
        universities = []
        file_path = Path(filename)
        
        if not file_path.exists():
            print(f"Error: File '{filename}' not found!")
            return universities
        
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('University Name', '').strip()
                url = row.get('URL', '').strip()
                
                if name:
                    universities.append({
                        'name': name,
                        'url': url if url else None
                    })
        
        print(f"✓ Loaded {len(universities)} universities")
        return universities
    
    def save_results(self, filename: str = 'trombone_faculty.csv'):
        """Save results to CSV"""
        if self.results:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['university', 'name', 'email', 'university_website', 'source']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.results)
            print(f"\n✓ Results saved to {filename}")
    
    async def run(self, input_file: str, output_file: str = 'trombone_faculty.csv'):
        """Main execution"""
        universities = self.load_universities(input_file)
        
        if not universities:
            print("No universities to process.")
            return
        
        await self.setup()
        
        try:
            print(f"\nProcessing {len(universities)} universities...")
            for uni in universities:
                await self.scrape_university(uni)
                await self.page.wait_for_timeout(2000)  # Be polite
        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
        finally:
            await self.cleanup()
        
        self.save_results(output_file)
        
        print(f"\n{'='*60}")
        print(f"COMPLETE!")
        print(f"✓ Found {len(self.results)} faculty members")
        print(f"✗ Failed for {len(self.failed_universities)} universities")


async def main():
    """Entry point"""
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'universities_sample.csv'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'trombone_faculty.csv'
    
    print("="*60)
    print("PLAYWRIGHT TROMBONE FACULTY SCRAPER")
    print("="*60)
    
    scraper = TromboneFacultyScraper()
    await scraper.run(input_file, output_file)


if __name__ == "__main__":
    asyncio.run(main())