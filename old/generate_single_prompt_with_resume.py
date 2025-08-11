#!/usr/bin/env python3
"""
Generates prompts for Claude Desktop to process ONE university at a time
WITH RESUME CAPABILITY - tracks URLs visited and can resume from last URL
"""

import csv
import json
from pathlib import Path

def get_current_university_status():
    """Check if there's an incomplete university from previous run"""
    incomplete_file = Path("tmp/incomplete_university.json")
    if incomplete_file.exists():
        with open(incomplete_file, 'r') as f:
            return json.load(f)
    return None

def get_next_university():
    """Get the next university to process, or resume incomplete one"""
    
    # Check for incomplete university first
    incomplete = get_current_university_status()
    if incomplete:
        return incomplete['index'], incomplete['university'], incomplete.get('last_url_visited')
    
    # Otherwise get next university normally
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
            return i + 1, reader[i], None  # No resume URL for new university
    
    return None, None, None

def generate_prompt():
    idx, uni, resume_url = get_next_university()
    
    if not uni:
        return "ALL UNIVERSITIES PROCESSED!"
    
    # Create URL tracking file path
    url_log_file = f"/Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/tmp/uni_{idx:03d}_urls.txt"
    
    # Base prompt parts
    prompt_header = f"""Process university #{idx} for trombone faculty:

FIRST: Create these tracking files:
1. URL log: {url_log_file}
2. Mark as incomplete: /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/tmp/incomplete_university.json
   Content: {{"index": {idx}, "university": {json.dumps(uni)}, "status": "processing"}}

UNIVERSITY #{idx}: {uni['University Name']}
"""

    if resume_url:
        # Resume prompt - start from specific URL
        prompt = prompt_header + f"""
RESUMING FROM PREVIOUS SESSION
Last URL visited: {resume_url}

IMPORTANT: This university was partially processed. Continue from where it left off.
Check the URL log at: {url_log_file}

STEPS:
1. Read the URL log to see what was already visited
2. Continue exploring from the last successful URL
3. For EACH new URL you visit, append it to: {url_log_file}
4. Search for remaining trombone faculty
5. APPEND new results to: /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/results/batches/uni_{idx:03d}.csv
6. When COMPLETE, delete the incomplete marker file
7. Update progress: Change LAST_PROCESSED={idx} in progress_tracker.txt

CRITICAL: 
- APPEND to existing CSV, don't overwrite
- Track every URL in the log file
- Say only: "Done #{idx}" when complete
"""
    else:
        # Fresh start prompt
        prompt = prompt_header + f"""
URL: {uni['URL']}

STEPS:
1. Navigate to URL
2. For EACH URL you visit (including the main one), append it to: {url_log_file}
   Format: One URL per line
3. Search for "trombone faculty"  
4. Write results to: /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/results/batches/uni_{idx:03d}.csv
   Headers: University,Faculty Name,Title,Email,Phone,Profile URL,Notes
5. When COMPLETE:
   - Delete incomplete marker: /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/tmp/incomplete_university.json
   - Update progress: Change LAST_PROCESSED={idx} in progress_tracker.txt
6. Say only: "Done #{idx}"

CRITICAL INSTRUCTIONS:
- Track EVERY URL you visit in the log file
- MINIMIZE OUTPUT - no explanations
- If NO trombone faculty, write to: /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/results/no_trombone_found.csv

If search doesn't work, try /faculty or /music URLs."""
    
    return prompt

if __name__ == "__main__":
    prompt = generate_prompt()
    
    # Save to file for Claude Desktop
    with open("current_prompt.txt", "w") as f:
        f.write(prompt)
    
    print("Prompt saved to current_prompt.txt")