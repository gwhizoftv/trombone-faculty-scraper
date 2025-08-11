#!/usr/bin/env python3
"""
Generates prompts for Claude Desktop to process ONE university at a time
"""

import csv
from pathlib import Path

def get_next_university():
    # Read progress
    progress_file = Path("progress_tracker.txt")
    try:
        with open(progress_file, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 1 and '=' in lines[0]:
                last_processed = int(lines[0].split('=')[1].strip())
            else:
                last_processed = int(lines[0].strip()) if lines else 0
    except (ValueError, IndexError):
        print("Warning: progress_tracker.txt format issue, resetting to 0")
        last_processed = 0
    
    # Read universities CSV
    universities_file = Path("music_schools_wikipedia.csv")
    with open(universities_file, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
    
    # Get next university with URL
    for i in range(last_processed, len(reader)):
        if reader[i]['URL']:
            return i + 1, reader[i]  # Return 1-based index
    
    return None, None

def generate_prompt():
    idx, uni = get_next_university()
    
    if not uni:
        return "ALL UNIVERSITIES PROCESSED!"
    
    prompt = f"""Process university #{idx} for trombone faculty:

FIRST: Create this EXACT file (DO NOT use any other filename):
/Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/results/batches/uni_{idx:03d}.csv

UNIVERSITY #{idx}: {uni['University Name']}
URL: {uni['URL']}

STEPS:
1. Navigate to URL
2. Search for "trombone faculty"  
3. Write results DIRECTLY to the file path shown above with headers:
   University,Faculty Name,Title,Email,Phone,Profile URL,Notes
4. DO NOT create trombone_faculty_results.csv or any other file!

CRITICAL INSTRUCTIONS:
- MINIMIZE OUTPUT - no explanations, no "I found...", no "Let me..."
- If NO trombone faculty, write to: /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/results/no_trombone_found.csv
- Update progress: Change LAST_PROCESSED={idx} in /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/progress_tracker.txt
- Say only: "Done #{idx}"

If search doesn't work, try /faculty or /music URLs."""
    
    return prompt

if __name__ == "__main__":
    prompt = generate_prompt()
    
    # Save to file for Claude Desktop
    with open("current_prompt.txt", "w") as f:
        f.write(prompt)
    
    print("Prompt saved to current_prompt.txt")