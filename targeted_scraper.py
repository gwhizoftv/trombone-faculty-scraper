#!/usr/bin/env python3
"""
Targeted scraper for specific university websites
Handles the search interfaces shown in the screenshots
"""

import asyncio
import csv
import re
from pathlib import Path
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page

class TargetedTromboneScraper:
    def __init__(self):
        self.results = []
        self.browser = None
        self.page = None
    
    async def setup(self):
        """Initialize Playwright"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)  # Set to False to see what's happening
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
    
    def extract_faculty_names(self, text: str) -> List[Dict]:
        """Extract faculty names from text"""
        faculty = []
        
        # Patterns from the screenshots
        patterns = [
            # Larry Isaacson | Boston Conservatory at Berklee
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\|\s*Boston Conservatory',
            # Norman Bolter | Boston Conservatory at Berklee  
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\|\s*Boston Conservatory',
            # Dylan Halliday, bass trombone
            r'([A-Z][a-z]+ [A-Z][a-z]+),\s*bass\s+trombone',
            # Andrew Ng, bass trombone
            r'([A-Z][a-z]+ [A-Z][a-z]+),\s*bass\s+trombone',
            # Michael Mulcahy and Daniel Chevallier, trombone
            r'([A-Z][a-z]+ [A-Z][a-z]+)(?:\s+and\s+([A-Z][a-z]+ [A-Z][a-z]+))?,\s*trombone',
            # Peter Ellefson: Current: Faculty
            r'([A-Z][a-z]+ [A-Z][a-z]+):\s*Current:\s*Faculty',
            # Wayne Wallace: Current: Faculty
            r'([A-Z][a-z]+ [A-Z][a-z]+):\s*Current:\s*Faculty',
            # Denson Paul Pollard: Current: Faculty
            r'([A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+):\s*Current:\s*Faculty',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    for name in match:
                        if name and len(name) > 5:
                            faculty.append({'name': name.strip()})
                else:
                    if match and len(match) > 5:
                        faculty.append({'name': match.strip()})
        
        # Remove duplicates
        seen = set()
        unique_faculty = []
        for f in faculty:
            if f['name'] not in seen:
                seen.add(f['name'])
                unique_faculty.append(f)
        
        return unique_faculty
    
    async def scrape_berklee(self):
        """Scrape Berklee College of Music"""
        print("\nScraping Berklee College of Music...")
        
        try:
            # Navigate to Berklee
            await self.page.goto("https://www.berklee.edu", timeout=15000)
            await self.page.wait_for_timeout(2000)
            
            # Click the search button (from screenshot)
            print("  Looking for search button...")
            search_button = await self.page.query_selector('button[aria-label*="search" i], .search-toggle, #search-button')
            if search_button:
                print("  Clicking search button...")
                await search_button.click()
                await self.page.wait_for_timeout(1000)
            
            # Find and fill search input
            print("  Looking for search input...")
            search_input = await self.page.query_selector('input[type="search"], input[type="text"][placeholder*="search" i]')
            if search_input:
                print("  Typing 'trombone'...")
                await search_input.fill("trombone")
                await search_input.press("Enter")
                await self.page.wait_for_timeout(3000)
                
                # Get results
                content = await self.page.inner_text('body')
                faculty = self.extract_faculty_names(content)
                
                for f in faculty:
                    f['university'] = 'Berklee College of Music'
                    f['url'] = 'https://www.berklee.edu'
                    self.results.append(f)
                    print(f"  ✓ Found: {f['name']}")
            else:
                print("  ✗ Could not find search input")
                
        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
    
    async def scrape_northwestern(self):
        """Scrape Northwestern University"""
        print("\nScraping Northwestern University...")
        
        try:
            # Direct link to search results from screenshot
            await self.page.goto("https://search.northwestern.edu/?q=trombone&as_sitesearch=https%3A%2F%2Fwww.music.northwestern.edu", timeout=15000)
            await self.page.wait_for_timeout(2000)
            
            content = await self.page.inner_text('body')
            faculty = self.extract_faculty_names(content)
            
            for f in faculty:
                f['university'] = 'Northwestern University'
                f['url'] = 'https://music.northwestern.edu'
                self.results.append(f)
                print(f"  ✓ Found: {f['name']}")
                
        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
    
    async def scrape_indiana(self):
        """Scrape Indiana University"""
        print("\nScraping Indiana University...")
        
        try:
            # Navigate to IU search page
            await self.page.goto("https://www.iu.edu/search/index.html", timeout=15000)
            await self.page.wait_for_timeout(2000)
            
            # Fill search
            search_input = await self.page.query_selector('input[type="text"], input[type="search"]')
            if search_input:
                await search_input.fill("trombone faculty")
                await search_input.press("Enter")
                await self.page.wait_for_timeout(3000)
                
                content = await self.page.inner_text('body')
                faculty = self.extract_faculty_names(content)
                
                for f in faculty:
                    f['university'] = 'Indiana University'
                    f['url'] = 'https://music.indiana.edu'
                    self.results.append(f)
                    print(f"  ✓ Found: {f['name']}")
                    
        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
    
    async def run(self):
        """Run the scraper"""
        await self.setup()
        
        try:
            await self.scrape_berklee()
            await self.scrape_northwestern()
            await self.scrape_indiana()
        finally:
            await self.cleanup()
        
        # Save results
        if self.results:
            with open('trombone_faculty_targeted.csv', 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['university', 'name', 'url'])
                writer.writeheader()
                writer.writerows(self.results)
            print(f"\n✓ Saved {len(self.results)} faculty members to trombone_faculty_targeted.csv")
        else:
            print("\n✗ No faculty found")

if __name__ == "__main__":
    scraper = TargetedTromboneScraper()
    asyncio.run(scraper.run())