#!/usr/bin/env python3
"""
Navigate and scrape trombone faculty from university websites
This script will interactively navigate to each school and search for faculty
"""

import asyncio
import csv
import re
from typing import List, Dict
from playwright.async_api import async_playwright
import time

class InteractiveTromboneScraper:
    def __init__(self, headless=False):
        self.results = []
        self.browser = None
        self.page = None
        self.headless = headless
        
    async def setup(self):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=500  # Slow down actions so we can see what's happening
        )
        self.page = await self.browser.new_page()
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        
    async def cleanup(self):
        """Clean up resources"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    def extract_faculty_names(self, text: str) -> List[str]:
        """Extract faculty names from page text"""
        names = []
        
        # Common patterns for faculty listings
        patterns = [
            # Name, trombone or Name, bass trombone
            r'([A-Z][a-z]+ [A-Z][a-z]+),\s*(?:bass\s+)?trombone',
            # Name | Institution (for search results)
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\|\s*[^|]*[Cc]onservatory',
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\|\s*[^|]*[Ss]chool',
            # Professor of Trombone: Name
            r'[Pp]rofessor of [Tt]rombone[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
            # Name, Professor of Trombone
            r'([A-Z][a-z]+ [A-Z][a-z]+),\s*[Pp]rofessor of [Tt]rombone',
            # Name followed by trombone in context
            r'([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+).*?teaches.*?trombone',
            r'([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+).*?trombone.*?faculty',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if match and len(match) > 4 and match not in names:
                    names.append(match)
        
        return names
    
    async def search_on_page(self, search_term: str) -> bool:
        """Try to search on the current page"""
        print(f"    Looking for search functionality...")
        
        # First, try to click a search button/icon to reveal search box
        search_button_selectors = [
            'button[aria-label*="search" i]',
            'a[aria-label*="search" i]',
            'button.search-button',
            'button.search-toggle',
            'button.search-icon',
            '.search-toggle',
            '#search-button',
            'button svg.search-icon',
            'a.search-link'
        ]
        
        for selector in search_button_selectors:
            try:
                button = await self.page.wait_for_selector(selector, timeout=1000)
                if button and await button.is_visible():
                    print(f"    Clicking search button: {selector}")
                    await button.click()
                    await self.page.wait_for_timeout(1000)
                    break
            except:
                continue
        
        # Now look for search input
        search_input_selectors = [
            'input[type="search"]',
            'input[name="s"]',
            'input[name="q"]',
            'input[name="search"]',
            'input[name="query"]',
            'input[placeholder*="search" i]',
            'input#search',
            'input.search-field',
            'input.search-input',
            '.search-box input',
            'form[role="search"] input[type="text"]'
        ]
        
        for selector in search_input_selectors:
            try:
                search_input = await self.page.wait_for_selector(selector, timeout=1000)
                if search_input and await search_input.is_visible():
                    print(f"    Found search input: {selector}")
                    await search_input.click()
                    await search_input.fill(search_term)
                    await search_input.press('Enter')
                    print(f"    Searched for: {search_term}")
                    await self.page.wait_for_load_state('networkidle', timeout=5000)
                    return True
            except:
                continue
        
        return False
    
    async def navigate_to_faculty_page(self) -> bool:
        """Try to navigate to a faculty/people page"""
        print("    Looking for faculty/people links...")
        
        # Look for links to faculty pages
        faculty_link_texts = [
            'Faculty', 'People', 'Faculty & Staff', 'Directory',
            'Our Faculty', 'Meet the Faculty', 'Faculty Directory',
            'Music Faculty', 'Brass Faculty', 'Wind Faculty'
        ]
        
        for link_text in faculty_link_texts:
            try:
                # Try to find by text content
                link = await self.page.get_by_text(link_text).first
                if link:
                    print(f"    Clicking link: {link_text}")
                    await link.click()
                    await self.page.wait_for_load_state('networkidle', timeout=5000)
                    return True
            except:
                continue
        
        # Try common faculty URLs
        current_url = self.page.url
        base_url = '/'.join(current_url.split('/')[:3])
        
        faculty_paths = [
            '/faculty', '/people', '/music/faculty', '/music/people',
            '/school-of-music/faculty', '/conservatory/faculty',
            '/directory', '/faculty-staff'
        ]
        
        for path in faculty_paths:
            try:
                url = base_url + path
                print(f"    Trying URL: {url}")
                await self.page.goto(url, wait_until='domcontentloaded', timeout=5000)
                content = await self.page.inner_text('body')
                if 'faculty' in content.lower() or 'people' in content.lower():
                    return True
            except:
                continue
        
        return False
    
    async def scrape_school(self, school_name: str, url: str = None):
        """Scrape a single school for trombone faculty"""
        print(f"\n{'='*60}")
        print(f"Scraping: {school_name}")
        
        if not url:
            # Try to construct a URL from the school name
            url_name = school_name.lower().replace(' ', '').replace(',', '')
            possible_urls = [
                f"https://www.{url_name}.edu",
                f"https://{url_name}.edu",
                f"https://www.{url_name.split()[0]}.edu"
            ]
            
            for test_url in possible_urls:
                try:
                    print(f"  Trying URL: {test_url}")
                    await self.page.goto(test_url, wait_until='domcontentloaded', timeout=5000)
                    url = test_url
                    break
                except:
                    continue
            
            if not url:
                print(f"  ✗ Could not find website for {school_name}")
                return
        else:
            try:
                print(f"  URL: {url}")
                await self.page.goto(url, wait_until='domcontentloaded', timeout=10000)
            except Exception as e:
                print(f"  ✗ Could not load website: {str(e)[:50]}")
                return
        
        # Strategy 1: Search for trombone faculty
        if await self.search_on_page("trombone faculty"):
            await self.page.wait_for_timeout(2000)
            content = await self.page.inner_text('body')
            names = self.extract_faculty_names(content)
            if names:
                for name in names[:3]:  # Take up to 3 names
                    self.results.append({
                        'school': school_name,
                        'name': name,
                        'url': url,
                        'method': 'search'
                    })
                    print(f"  ✓ Found: {name}")
                return
        
        # Strategy 2: Try just "trombone"
        if await self.search_on_page("trombone"):
            await self.page.wait_for_timeout(2000)
            content = await self.page.inner_text('body')
            names = self.extract_faculty_names(content)
            if names:
                for name in names[:3]:
                    self.results.append({
                        'school': school_name,
                        'name': name,
                        'url': url,
                        'method': 'search'
                    })
                    print(f"  ✓ Found: {name}")
                return
        
        # Strategy 3: Navigate to faculty page
        if await self.navigate_to_faculty_page():
            content = await self.page.inner_text('body')
            if 'trombone' in content.lower():
                names = self.extract_faculty_names(content)
                if names:
                    for name in names[:2]:
                        self.results.append({
                            'school': school_name,
                            'name': name,
                            'url': url,
                            'method': 'faculty_page'
                        })
                        print(f"  ✓ Found: {name}")
                    return
        
        print(f"  ✗ No trombone faculty found")
    
    async def run_on_schools(self, schools_file: str):
        """Run scraper on a list of schools"""
        # Load schools
        schools = []
        with open(schools_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                schools.append({
                    'name': row.get('University Name', ''),
                    'url': row.get('URL', '')
                })
        
        await self.setup()
        
        try:
            print(f"Processing {len(schools)} schools...")
            print("(Set headless=False to see browser actions)")
            
            for i, school in enumerate(schools[:10], 1):  # Process first 10 as a test
                print(f"\n[{i}/{min(10, len(schools))}]", end=" ")
                await self.scrape_school(school['name'], school['url'])
                await self.page.wait_for_timeout(1000)  # Be polite between requests
                
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        finally:
            await self.cleanup()
        
        # Save results
        if self.results:
            output_file = 'trombone_faculty_interactive.csv'
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['school', 'name', 'url', 'method'])
                writer.writeheader()
                writer.writerows(self.results)
            print(f"\n✓ Saved {len(self.results)} faculty members to {output_file}")
        else:
            print("\n✗ No faculty found")

async def main():
    """Main entry point"""
    import sys
    
    # Parse arguments
    headless = '--headless' in sys.argv
    if '--headless' in sys.argv:
        sys.argv.remove('--headless')
    
    schools_file = sys.argv[1] if len(sys.argv) > 1 else 'universities_sample.csv'
    
    print("="*60)
    print("INTERACTIVE TROMBONE FACULTY SCRAPER")
    print("="*60)
    print(f"Mode: {'Headless' if headless else 'Visible browser'}")
    print(f"Input: {schools_file}")
    print("")
    
    scraper = InteractiveTromboneScraper(headless=headless)
    await scraper.run_on_schools(schools_file)

if __name__ == "__main__":
    asyncio.run(main())