#!/usr/bin/env python3
"""
Generates a VERY simple prompt for Claude Desktop to avoid hitting limits
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
                last_processed = 0
    except:
        last_processed = 0
    
    # Read universities CSV
    universities_file = Path("music_schools_wikipedia.csv")
    with open(universities_file, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
    
    # Get next university with URL
    for i in range(last_processed, len(reader)):
        if reader[i]['URL']:
            return i + 1, reader[i]
    
    return None, None

def generate_prompt():
    idx, uni = get_next_university()
    
    if not uni:
        return "ALL UNIVERSITIES PROCESSED!"
    
    # EXTREMELY SIMPLE PROMPT
    prompt = f"""UNIVERSITY #{idx}: {uni['University Name']}
URL: {uni['URL']}

1. Go to URL
2. Search for "trombone faculty"  
3. Save results to: /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/results/batches/uni_{idx:03d}.csv
4. Update progress: LAST_PROCESSED={idx} in progress_tracker.txt
5. Say only: "Done {idx}"

NO EXPLANATIONS. NO TOOL DESCRIPTIONS."""
    
    return prompt

if __name__ == "__main__":
    prompt = generate_prompt()
    with open("current_prompt.txt", "w") as f:
        f.write(prompt)
    print("Simple prompt saved")