#!/usr/bin/env python3
"""
Script for Claude Desktop to execute using MCP servers.
Claude Desktop will read this script and use its Playwright and filesystem MCP servers
to intelligently navigate university websites and extract trombone faculty information.
"""

import csv
import json
from pathlib import Path

# Instructions for Claude Desktop when running this script
CLAUDE_INSTRUCTIONS = """
You have access to Playwright MCP and filesystem MCP servers. 
For each university in the CSV file, you need to:

1. Navigate to the university website
2. QUICKLY find search - CHECK THESE LOCATIONS IN ORDER:
   a. TOP RIGHT corner of page (90% of sites put search here)
   b. TOP navigation bar/header
   c. Look for magnifying glass icon (🔍) in header
   d. "Search" text link in top navigation
3. Search for "trombone faculty" or "trombone professor" (NOT just "trombone")
4. Click on each trombone faculty member's profile
5. EXTRACT CONTACT INFO (CRITICAL):
   - Email address (look for @ symbol, mailto: links)
   - Phone number (look for patterns like xxx-xxx-xxxx, (xxx) xxx-xxxx)
   - Name and title
   - Profile URL
6. Save the results to a CSV file with ALL contact information

SPEED TIPS TO FIND SEARCH FASTER:
- FIRST: Check top-right corner (most common location)
- Look for these selectors quickly:
  * button[aria-label*="search" i]
  * .search-icon, .search-button, .search-toggle
  * svg with magnifying glass shape in header
  * input[type="search"] or input[placeholder*="search" i]
- Don't scan the entire page - focus on header/top area first
- If no search in header after 10 seconds, try direct URL patterns:
  * /search, /faculty, /directory, /people

BETTER SEARCH TERMS (use these instead of just "trombone"):
- "trombone faculty" (most effective)
- "trombone professor"
- "brass faculty" then look for trombone
- faculty name if you know it (e.g., from previous research)

Be intelligent and adaptive:
- If search doesn't work, try navigating through menus (Music Department, Faculty, etc.)
- Look for patterns in URLs (e.g., /faculty, /people, /directory)
- Handle different page layouts and structures
- If one approach fails, try another

Remember: You can SEE the page, so make intelligent decisions about what to click.
"""

def main():
    # Read the universities CSV
    universities_file = Path("music_schools_wikipedia.csv")
    output_file = Path("trombone_faculty_results.csv")
    
    print(f"Reading universities from {universities_file}")
    print("\nCLAUDE DESKTOP INSTRUCTIONS:")
    print(CLAUDE_INSTRUCTIONS)
    
    # Read universities to process
    universities = []
    with open(universities_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['URL']:  # Only process if URL exists
                universities.append(row)
    
    print(f"\nFound {len(universities)} universities to process")
    
    # Initialize output CSV
    output_headers = ['University', 'Faculty Name', 'Title', 'Email', 'Phone', 'Profile URL', 'Notes']
    
    print(f"\nSTART SCRAPING PROCESS:")
    print(f"Output will be saved to: {output_file}")
    print("\n" + "="*60)
    
    # Process each university
    for idx, uni in enumerate(universities[:5], 1):  # Start with first 5 for testing
        print(f"\n[{idx}/5] Processing: {uni['University Name']}")
        print(f"URL: {uni['URL']}")
        print(f"Type: {uni['Type']}")
        
        print("\nCLAUDE ACTION REQUIRED:")
        print(f"1. Use @playwright to navigate to {uni['URL']}")
        print("2. QUICK SEARCH LOCATION CHECK (in order):")
        print("   - TOP RIGHT corner first (most common)")
        print("   - Header/navigation bar")
        print("   - Look for 🔍 magnifying glass icon")
        print("   - If not found in 10 seconds, try URL: {uni['URL']}/search or /faculty")
        print("3. Search for 'trombone faculty' or 'trombone professor' (better than just 'trombone')")
        print("4. Click each faculty profile and EXTRACT EMAIL + PHONE")
        print("5. Use @filesystem to append results (with email/phone) to trombone_faculty_results.csv")
        
        print("\nFAST SEARCH SELECTORS TO TRY:")
        print("- button[aria-label*='search' i]")
        print("- .search-icon, .search-button (in header)")
        print("- input[type='search']")
        print("- svg or icon in top-right corner")
        
        print("\nIf no search found quickly, try direct navigation:")
        print("- Menu items: 'Faculty', 'People', 'Directory', 'Music Department'")
        print("- Direct URLs: /faculty, /people, /directory, /music")
        print("- Look for 'Brass' or 'Woodwinds, Brass & Percussion' sections")
        
        print("\nCRITICAL DATA TO EXTRACT FROM EACH FACULTY PAGE:")
        print("- Full name")
        print("- Title (e.g., 'Associate Professor of Trombone')")
        print("- EMAIL ADDRESS (REQUIRED - look for @ symbol, mailto: links)")
        print("- PHONE NUMBER (if available - patterns: xxx-xxx-xxxx, (xxx) xxx-xxxx, xxx.xxx.xxxx)")
        print("- Profile page URL")
        print("- Any additional notes (department, specialization, office location)")
        
        print("\nEMAIL FINDING TIPS:")
        print("- Look for 'mailto:' links")
        print("- Check for @ symbols in text")
        print("- Sometimes hidden in 'Contact' or 'Email' sections")
        print("- May need to click 'Show email' or 'Contact info' button")
        
        print("\nPHONE FINDING TIPS:")
        print("- Look for 'Phone:', 'Tel:', 'Office:' labels")
        print("- Check contact cards or info boxes")
        print("- Usually formatted with dashes, dots, or parentheses")
        print("- May include extension (e.g., x1234 or ext. 1234)")
        
        print("\n" + "-"*40)
        
        # This is where Claude Desktop would execute the MCP commands
        # The script provides the structure and prompts for Claude to follow
        
    print("\n" + "="*60)
    print("SCRAPING COMPLETE")
    print(f"Results should be saved in: {output_file}")
    print("\nTo continue with remaining universities, modify the script to process more than 5.")

if __name__ == "__main__":
    main()