#!/usr/bin/env python3
"""
Interactive Playwright MCP Faculty Scraper
This script helps coordinate the interactive scraping process using Playwright MCP
"""

import csv
import re
from pathlib import Path
from typing import List, Dict

class FacultyDataProcessor:
    def __init__(self):
        self.results = []
        self.failed_universities = []
    
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
    
    def extract_faculty_from_text(self, text: str, university_name: str) -> List[Dict]:
        """Extract faculty information from page text"""
        found_faculty = []
        
        # Clean the text
        text = re.sub(r'\s+', ' ', text)
        
        # Strategy 1: Look for names near "trombone" mentions
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'trombone' in line.lower():
                # Check this line and nearby lines for names
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    potential_name = lines[j].strip()
                    # Remove common prefixes
                    potential_name = re.sub(r'^(Professor|Dr\.|Mr\.|Ms\.|Mrs\.)\s+', '', potential_name)
                    
                    if self.is_valid_name(potential_name):
                        context = ' '.join(lines[max(0, j-2):min(len(lines), j+3)])
                        emails = self.extract_emails(context)
                        
                        faculty_member = {
                            'name': potential_name,
                            'email': emails[0] if emails else None,
                            'university': university_name,
                            'source': 'Interactive Playwright Scrape'
                        }
                        
                        # Avoid duplicates
                        if not any(f['name'] == potential_name for f in found_faculty):
                            found_faculty.append(faculty_member)
        
        # Strategy 2: Pattern matching for specific formats
        patterns = [
            # Larry Isaacson | Boston Conservatory at Berklee
            r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*\|\s*[^|]*(?:trombone|Trombone)',
            # Dylan Halliday, bass trombone
            r'([A-Z][a-z]+ [A-Z][a-z]+),\s*(?:bass\s+)?trombone',
            # Andrew Ng, bass trombone
            r'([A-Z][a-z]+\s+[A-Z][a-z]+),\s*(?:bass\s+)?trombone',
            # Professor of Trombone: Name
            r'Professor of (?:T|t)rombone[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
            # Norman Bolter format
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s+is an? (?:assistant\s+)?professor of trombone',
            # Peter Ellefson: ... Faculty ... Trombone
            r'([A-Z][a-z]+ [A-Z][a-z]+):\s*[^:]*Faculty[^:]*(?:T|t)rombone',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if self.is_valid_name(match):
                    # Find email near this name
                    name_index = text.find(match)
                    if name_index != -1:
                        context = text[max(0, name_index-200):name_index+200]
                        emails = self.extract_emails(context)
                        
                        faculty_member = {
                            'name': match,
                            'email': emails[0] if emails else None,
                            'university': university_name,
                            'source': 'Interactive Playwright Pattern Match'
                        }
                        
                        if not any(f['name'] == match for f in found_faculty):
                            found_faculty.append(faculty_member)
        
        return found_faculty
    
    def add_faculty(self, faculty_list: List[Dict]):
        """Add faculty to results, avoiding duplicates"""
        for faculty in faculty_list:
            if not any(r['name'] == faculty['name'] and r['university'] == faculty['university'] 
                      for r in self.results):
                self.results.append(faculty)
                print(f"  ✓ Added: {faculty['name']} at {faculty['university']}")
                if faculty.get('email'):
                    print(f"    Email: {faculty['email']}")
    
    def save_results(self, filename: str = 'trombone_faculty.csv'):
        """Save results to CSV file"""
        if self.results:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['university', 'name', 'email', 'source']
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.results)
            print(f"\n✓ Results saved to {filename}")
            print(f"  Found {len(self.results)} faculty members")
        else:
            print("\n✗ No results to save")
    
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


# Example usage for processing scraped content
if __name__ == "__main__":
    processor = FacultyDataProcessor()
    
    # This would be called after scraping each university with Playwright MCP
    # Example:
    # scraped_text = "Larry Isaacson | Boston Conservatory at Berklee..."
    # faculty = processor.extract_faculty_from_text(scraped_text, "Berklee College of Music")
    # processor.add_faculty(faculty)
    
    print("Faculty Data Processor ready.")
    print("Use this to process scraped content from Playwright MCP.")