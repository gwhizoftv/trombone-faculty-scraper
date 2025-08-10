#!/usr/bin/env python3
"""
Visual Interactive Scraper for Trombone Faculty
This script opens a visible browser and navigates through each university website,
searching for trombone faculty and clicking on their profiles.
"""

import asyncio
import csv
import re
import json
from typing import List, Dict
from playwright.async_api import async_playwright
import time

class VisualTromboneScraper:
    def __init__(self):
        self.results = []
        self.browser = None
        self.page = None
        
    async def setup(self):
        """Initialize Playwright with a visible browser"""
        self.playwright = await async_playwright().start()
        # Launch browser in non-headless mode so you can see what's happening
        self.browser = await self.playwright.chromium.launch(
            headless=False,  # Show the browser window
            slow_mo=1000,    # Slow down actions by 1 second so you can see them
            args=['--start-maximized']
        )
        context = await self.browser.new_context(viewport={'width': 1920, 'height': 1080})
        self.page = await context.new_page()
        
    async def cleanup(self):
        """Clean up resources"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def click_search_button(self):
        """Try to find and click a search button/icon"""
        print("    Looking for search button...")
        
        search_selectors = [
            'button[aria-label*="search" i]',
            'a[aria-label*="search" i]',
            'button[class*="search" i]',
            'a[class*="search" i]',
            'button[id*="search" i]',
            '.search-toggle',
            '.search-button',
            '.search-icon',
            'svg[class*="search" i]',
            'i[class*="search" i]'
        ]
        
        for selector in search_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=2000)
                if element and await element.is_visible():
                    print(f"    Found search element: {selector}")
                    await element.click()
                    await self.page.wait_for_timeout(1500)
                    return True
            except:
                continue
        return False
    
    async def search_for_term(self, search_term: str):
        """Enter search term and submit"""
        print(f"    Searching for: {search_term}")
        
        # Look for search input
        input_selectors = [
            'input[type="search"]',
            'input[name="s"]',
            'input[name="q"]',
            'input[name="search"]',
            'input[placeholder*="search" i]',
            'input[id*="search" i]',
            'input[class*="search" i]',
            'form[role="search"] input[type="text"]'
        ]
        
        for selector in input_selectors:
            try:
                input_element = await self.page.wait_for_selector(selector, timeout=2000)
                if input_element and await input_element.is_visible():
                    print(f"    Found search input: {selector}")
                    await input_element.click()
                    await input_element.fill("")  # Clear first
                    await input_element.type(search_term, delay=100)  # Type slowly
                    await self.page.wait_for_timeout(500)
                    await input_element.press('Enter')
                    print("    Submitted search")
                    await self.page.wait_for_load_state('networkidle', timeout=10000)
                    return True
            except:
                continue
        return False
    
    async def extract_faculty_from_results(self):
        """Extract faculty information from search results"""
        faculty = []
        
        # Wait for results to load
        await self.page.wait_for_timeout(2000)
        
        # Get all text content
        content = await self.page.content()
        text = await self.page.inner_text('body')
        
        # Look for faculty names in various formats
        patterns = [
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*[,|\-]\s*(?:bass\s+)?trombone',
            r'([A-Z][a-z]+ [A-Z][a-z]+).*?[Pp]rofessor of [Tt]rombone',
            r'([A-Z][a-z]+ [A-Z][a-z]+).*?[Tt]rombone [Ff]aculty',
            r'([A-Z][a-z]+ [A-Z][a-z]+).*?teaches trombone'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match not in [f['name'] for f in faculty]:
                    faculty.append({'name': match, 'role': 'Trombone Faculty'})
        
        # Try to find clickable links to faculty profiles
        print("    Looking for faculty profile links...")
        
        # Find all links that might be faculty profiles
        links = await self.page.query_selector_all('a')
        for link in links[:50]:  # Check first 50 links
            try:
                link_text = await link.inner_text()
                href = await link.get_attribute('href')
                
                # Check if link text looks like a faculty name
                if link_text and re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+', link_text):
                    # Check if surrounding text mentions trombone
                    parent = await link.evaluate_handle('el => el.parentElement')
                    parent_text = await parent.inner_text() if parent else ""
                    
                    if 'trombone' in parent_text.lower():
                        if link_text not in [f['name'] for f in faculty]:
                            faculty.append({
                                'name': link_text,
                                'role': 'Trombone Faculty',
                                'profile_url': href
                            })
                            print(f"      Found faculty link: {link_text}")
            except:
                continue
        
        return faculty
    
    async def click_faculty_profiles(self, faculty_list):
        """Click on each faculty profile to get more information"""
        enhanced_faculty = []
        
        for faculty in faculty_list:
            if 'profile_url' in faculty:
                print(f"    Visiting profile: {faculty['name']}")
                try:
                    # Navigate to profile
                    await self.page.goto(faculty['profile_url'], wait_until='domcontentloaded', timeout=10000)
                    await self.page.wait_for_timeout(2000)
                    
                    # Extract additional info
                    profile_text = await self.page.inner_text('body')
                    
                    # Look for email
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', profile_text)
                    if email_match:
                        faculty['email'] = email_match.group()
                    
                    # Look for title
                    title_patterns = [
                        r'(Assistant |Associate |Full )?Professor',
                        r'Lecturer',
                        r'Instructor'
                    ]
                    for pattern in title_patterns:
                        if re.search(pattern, profile_text, re.IGNORECASE):
                            faculty['title'] = pattern
                            break
                    
                    enhanced_faculty.append(faculty)
                    
                    # Go back to search results
                    await self.page.go_back()
                    await self.page.wait_for_timeout(2000)
                    
                except Exception as e:
                    print(f"      Could not visit profile: {e}")
                    enhanced_faculty.append(faculty)
            else:
                enhanced_faculty.append(faculty)
        
        return enhanced_faculty
    
    async def scrape_university(self, name: str, url: str):
        """Scrape a single university"""
        print(f"\n{'='*60}")
        print(f"Scraping: {name}")
        print(f"URL: {url}")
        
        try:
            # Navigate to the university website
            print("  Navigating to website...")
            await self.page.goto(url, wait_until='domcontentloaded', timeout=15000)
            await self.page.wait_for_timeout(2000)
            
            # Try to click search button
            if await self.click_search_button():
                # Search for trombone faculty
                if await self.search_for_term("trombone faculty"):
                    # Extract faculty from results
                    faculty = await self.extract_faculty_from_results()
                    
                    if faculty:
                        print(f"  Found {len(faculty)} faculty members")
                        
                        # Try to click on their profiles
                        faculty = await self.click_faculty_profiles(faculty)
                        
                        # Add to results
                        for f in faculty:
                            self.results.append({
                                'university': name,
                                'name': f['name'],
                                'role': f.get('role', ''),
                                'email': f.get('email', ''),
                                'title': f.get('title', ''),
                                'url': url
                            })
                            print(f"  ✓ {f['name']}")
                    else:
                        print("  No faculty found in search results")
                else:
                    print("  Could not perform search")
            else:
                # Try alternate search for "trombone"
                print("  Trying alternate search...")
                if await self.search_for_term("trombone"):
                    faculty = await self.extract_faculty_from_results()
                    for f in faculty[:3]:  # Take up to 3
                        self.results.append({
                            'university': name,
                            'name': f['name'],
                            'role': f.get('role', ''),
                            'email': f.get('email', ''),
                            'url': url
                        })
                        print(f"  ✓ {f['name']}")
                        
        except Exception as e:
            print(f"  Error: {str(e)[:100]}")
    
    async def run(self, universities_file: str, output_file: str = 'faculty_visual.csv'):
        """Run the scraper on universities"""
        # Load universities
        universities = []
        with open(universities_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('URL'):  # Only process if URL exists
                    universities.append({
                        'name': row['University Name'],
                        'url': row['URL']
                    })
        
        print(f"Loaded {len(universities)} universities with URLs")
        
        await self.setup()
        
        try:
            # Process universities
            for i, uni in enumerate(universities[:5], 1):  # Start with first 5
                print(f"\n[{i}/5] Processing...")
                await self.scrape_university(uni['name'], uni['url'])
                
                # Ask if user wants to continue
                if i < 5 and i < len(universities):
                    print("\nPress Enter to continue to next university, or Ctrl+C to stop...")
                    await self.page.wait_for_timeout(3000)
                    
        except KeyboardInterrupt:
            print("\n\nStopped by user")
        finally:
            await self.cleanup()
        
        # Save results
        if self.results:
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, 
                    fieldnames=['university', 'name', 'role', 'title', 'email', 'url'])
                writer.writeheader()
                writer.writerows(self.results)
            print(f"\n✓ Saved {len(self.results)} faculty to {output_file}")

async def main():
    print("="*60)
    print("VISUAL TROMBONE FACULTY SCRAPER")
    print("="*60)
    print("\nThis will open a browser window that you can watch.")
    print("The script will navigate to each university and search for faculty.")
    print("\nStarting in 3 seconds...")
    await asyncio.sleep(3)
    
    scraper = VisualTromboneScraper()
    
    # Use the updated music_schools file with URLs
    await scraper.run('music_schools_wikipedia.csv')

if __name__ == "__main__":
    asyncio.run(main())