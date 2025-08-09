#!/usr/bin/env python3
"""
Playwright-based Trombone Faculty Scraper
Uses the Playwright MCP server to scrape faculty information from university websites
"""

import csv
import re
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import subprocess
import sys

class PlaywrightFacultyScraper:
    def __init__(self):
        self.results = []
        self.failed_universities = []
        self.playwright_command = ["npx", "@playwright/mcp@latest"]
        
    def run_playwright_mcp(self, action: str, params: Dict) -> Dict:
        """Execute a Playwright MCP server command"""
        request = {
            "jsonrpc": "2.0",
            "method": action,
            "params": params,
            "id": 1
        }
        
        try:
            # Run the MCP server command
            process = subprocess.Popen(
                self.playwright_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send the JSON-RPC request
            stdout, stderr = process.communicate(input=json.dumps(request))
            
            if stderr:
                print(f"  Warning: {stderr}")
            
            # Parse the response
            if stdout:
                response = json.loads(stdout)
                if "result" in response:
                    return response["result"]
                elif "error" in response:
                    print(f"  Error: {response['error']}")
                    return {}
            
            return {}
            
        except Exception as e:
            print(f"  MCP execution error: {e}")
            return {}
    
    def navigate_to_url(self, url: str) -> bool:
        """Navigate to a URL using Playwright"""
        result = self.run_playwright_mcp("navigate", {"url": url})
        return result.get("success", False)
    
    def search_on_page(self, search_term: str) -> Optional[str]:
        """Search for content on the current page"""
        # First try to find a search box
        search_selectors = [
            "input[type='search']",
            "input[name='s']",
            "input[name='q']",
            "input[name='search']",
            "input[placeholder*='earch' i]",
            "input#search",
            "input[aria-label*='earch' i]"
        ]
        
        for selector in search_selectors:
            # Try to fill the search box
            result = self.run_playwright_mcp("fill", {
                "selector": selector,
                "text": search_term
            })
            
            if result.get("success"):
                # Press Enter to submit
                self.run_playwright_mcp("press", {
                    "selector": selector,
                    "key": "Enter"
                })
                
                # Wait for navigation
                time.sleep(3)
                
                # Get the page content
                content_result = self.run_playwright_mcp("get_content", {})
                return content_result.get("content", "")
        
        return None
    
    def get_page_content(self) -> str:
        """Get the current page content"""
        result = self.run_playwright_mcp("get_content", {})
        return result.get("content", "")
    
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
            'undergraduate', 'graduate', 'diploma', 'degree', 'bachelor', 'master',
            'performance', 'ensemble', 'orchestra', 'symphony', 'philharmonic',
            'saxophone', 'trumpet', 'tuba', 'horn', 'jazz', 'tenor', 'alto'
        }
        
        all_non_names = all(part.lower() in non_name_words for part in parts)
        if all_non_names:
            return False
        
        has_proper_name = any(p[0].isupper() for p in parts if p)
        return has_proper_name and len(parts) >= 2
    
    def extract_trombone_faculty(self, content: str) -> List[Dict]:
        """Extract trombone faculty information from page content"""
        results = []
        
        # Pattern 1: Name followed by trombone designation
        patterns = [
            r'([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+(?:-[A-Z][a-z]+)?),?\s*(?:bass\s+)?trombone',
            r'(?:bass\s+)?[Tt]rombone\s*(?:–|-|:|,)\s*([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+(?:-[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s*\((?:bass\s+)?[Tt]rombone\)',
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s+(?:[Tt]rombone\s+[Ff]aculty|[Pp]rofessor\s+of\s+[Tt]rombone)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if self.is_valid_name(match):
                    # Find email near this name
                    name_index = content.find(match)
                    context = content[max(0, name_index-200):name_index+200]
                    emails = self.extract_emails(context)
                    
                    if not any(r['name'] == match for r in results):
                        results.append({
                            'name': match,
                            'email': emails[0] if emails else None
                        })
        
        # Pattern 2: Look for sections mentioning trombone and extract nearby names
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'trombone' in line.lower():
                # Check lines around this one for names
                for j in range(max(0, i-3), min(len(lines), i+4)):
                    potential_name = lines[j].strip()
                    # Clean HTML tags if present
                    potential_name = re.sub(r'<[^>]+>', '', potential_name)
                    potential_name = potential_name.strip()
                    
                    if self.is_valid_name(potential_name):
                        context = '\n'.join(lines[max(0, j-2):min(len(lines), j+3)])
                        emails = self.extract_emails(context)
                        
                        if not any(r['name'] == potential_name for r in results):
                            results.append({
                                'name': potential_name,
                                'email': emails[0] if emails else None
                            })
        
        return results
    
    def scrape_university(self, uni_info: Dict) -> None:
        """Scrape a single university for trombone faculty"""
        name = uni_info['name']
        base_url = uni_info.get('url', '')
        
        print(f"\n{'='*60}")
        print(f"Scraping {name}...")
        
        if not base_url:
            print(f"  ✗ No URL provided for {name}")
            self.failed_universities.append(name)
            return
        
        # Navigate to the university website
        if not self.navigate_to_url(base_url):
            print(f"  ✗ Could not navigate to {base_url}")
            self.failed_universities.append(name)
            return
        
        # Strategy 1: Try searching for trombone faculty
        print(f"  Searching for 'trombone faculty'...")
        search_content = self.search_on_page("trombone faculty")
        
        if search_content:
            faculty = self.extract_trombone_faculty(search_content)
            if faculty:
                for f in faculty[:3]:  # Take up to 3 results
                    f['university'] = name
                    f['university_website'] = base_url
                    f['source'] = 'Search'
                    self.results.append(f)
                    print(f"  ✓ Found: {f['name']}")
                    if f.get('email'):
                        print(f"    Email: {f['email']}")
                return
        
        # Strategy 2: Try common faculty page URLs
        faculty_paths = [
            '/music/faculty',
            '/faculty',
            '/people',
            '/music/people',
            '/school-of-music/faculty'
        ]
        
        for path in faculty_paths:
            full_url = base_url.rstrip('/') + path
            print(f"  Trying {path}...")
            
            if self.navigate_to_url(full_url):
                content = self.get_page_content()
                if 'trombone' in content.lower():
                    faculty = self.extract_trombone_faculty(content)
                    if faculty:
                        f = faculty[0]
                        f['university'] = name
                        f['university_website'] = base_url
                        f['source'] = 'Faculty Page'
                        self.results.append(f)
                        print(f"  ✓ Found: {f['name']}")
                        if f.get('email'):
                            print(f"    Email: {f['email']}")
                        return
        
        print(f"  ✗ No trombone faculty found")
        self.failed_universities.append(name)
    
    def load_universities(self, filename: str) -> List[Dict]:
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
                    name = row.get('University Name', '').strip()
                    url = row.get('URL', '').strip()
                    
                    if name:
                        universities.append({
                            'name': name,
                            'url': url if url else None
                        })
            
            print(f"✓ Loaded {len(universities)} universities from {filename}")
            return universities
            
        except Exception as e:
            print(f"Error loading file '{filename}': {e}")
            return []
    
    def save_results(self, filename: str = 'trombone_faculty.csv') -> None:
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
    
    def run(self, input_file: str, output_file: str = 'trombone_faculty.csv') -> None:
        """Main execution method"""
        universities = self.load_universities(input_file)
        
        if not universities:
            print("No universities to process.")
            return
        
        print(f"\nProcessing {len(universities)} universities...")
        print("Press Ctrl+C to stop.\n")
        
        try:
            for uni_info in universities:
                self.scrape_university(uni_info)
                time.sleep(2)  # Be polite between requests
        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
        
        self.save_results(output_file)
        
        # Summary
        print(f"\n{'='*60}")
        print(f"COMPLETE!")
        print(f"✓ Found {len(self.results)} trombone faculty members")
        print(f"✗ Failed for {len(self.failed_universities)} universities")
        
        if self.results:
            print(f"\nResults:")
            for result in self.results:
                print(f"  • {result['name']} at {result['university']}")
                if result.get('email'):
                    print(f"    {result['email']}")


def main():
    """Main entry point"""
    scraper = PlaywrightFacultyScraper()
    
    # Get input/output files
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'trombone_faculty.csv'
    else:
        print("="*60)
        print("PLAYWRIGHT TROMBONE FACULTY SCRAPER")
        print("="*60)
        print("\nUsage:")
        print("  python playwright_faculty_scraper.py [input.csv] [output.csv]")
        print("")
        
        input_file = input("Enter input file (default: universities_sample.csv): ").strip()
        if not input_file:
            input_file = 'universities_sample.csv'
        
        output_file = input("Enter output file (default: trombone_faculty.csv): ").strip()
        if not output_file:
            output_file = 'trombone_faculty.csv'
    
    scraper.run(input_file, output_file)


if __name__ == "__main__":
    main()