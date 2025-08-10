#!/usr/bin/env python3
"""
Single university scraper for Claude Desktop - processes ONE university at a time
to avoid context length issues. Run multiple times for different universities.
"""

import csv
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python single_university_scraper.py <row_number>")
        print("Example: python single_university_scraper.py 1")
        print("\nThis will process the university at row N in music_schools_wikipedia.csv")
        sys.exit(1)
    
    row_num = int(sys.argv[1])
    
    # Read the specific university
    universities_file = Path("music_schools_wikipedia.csv")
    output_file = Path("trombone_faculty_results.csv")
    
    with open(universities_file, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        if row_num > len(reader) or row_num < 1:
            print(f"Error: Row {row_num} not found. CSV has {len(reader)} universities.")
            sys.exit(1)
        
        uni = reader[row_num - 1]  # Convert to 0-based index
    
    if not uni['URL']:
        print(f"Skipping {uni['University Name']} - no URL provided")
        sys.exit(0)
    
    print("="*60)
    print(f"PROCESSING UNIVERSITY #{row_num}")
    print(f"Name: {uni['University Name']}")
    print(f"URL: {uni['URL']}")
    print(f"Type: {uni['Type']}")
    print("="*60)
    
    print("\nQUICK INSTRUCTIONS FOR CLAUDE DESKTOP:")
    print("1. Navigate to the URL above")
    print("2. Find search (CHECK TOP-RIGHT CORNER FIRST!)")
    print("3. Search for 'trombone faculty' or 'trombone professor'")
    print("4. Click each trombone faculty profile")
    print("5. EXTRACT: Name, Title, EMAIL (required), PHONE (if available)")
    print("6. Save to trombone_faculty_results.csv")
    
    print("\nFAST SEARCH TIPS:")
    print("- TOP RIGHT corner (90% of sites)")
    print("- Look for 🔍 icon")
    print("- Try: button[aria-label*='search']")
    print("- If no search after 10 sec, try: {}/faculty".format(uni['URL']))
    
    print("\nEXTRACT FROM EACH PROFILE:")
    print("✓ Email (look for @ or mailto:)")
    print("✓ Phone (xxx-xxx-xxxx patterns)")
    print("✓ Full name and title")
    print("✓ Profile URL")
    
    print("\nWhen done, run next university:")
    print(f"python single_university_scraper.py {row_num + 1}")
    print("-"*60)

if __name__ == "__main__":
    main()