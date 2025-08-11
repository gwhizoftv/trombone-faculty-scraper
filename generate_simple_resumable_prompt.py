#!/usr/bin/env python3
"""
Simplified prompt generator with URL tracking for resume capability
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

def check_for_resume(idx):
    """Check if we need to resume from a previous incomplete run"""
    url_log = Path(f"tmp/uni_{idx:03d}_urls.txt")
    if url_log.exists() and url_log.stat().st_size > 0:
        with open(url_log, 'r') as f:
            urls = f.readlines()
            if urls:
                return urls[-1].strip()  # Return last URL visited
    return None

def generate_prompt():
    idx, uni = get_next_university()
    
    if not uni:
        return "ALL UNIVERSITIES PROCESSED!"
    
    # Check if we're resuming
    last_url = check_for_resume(idx)
    
    # Create URL tracking file path
    url_log_file = f"/Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/tmp/uni_{idx:03d}_urls.txt"
    batch_file = f"/Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/results/batches/uni_{idx:03d}.csv"
    
    if last_url:
        # Resume prompt
        prompt = f"""RESUMING university #{idx}: {uni['University Name']}

Last URL visited: {last_url}
Continue from there and find remaining trombone faculty.

CRITICAL:
1. APPEND to existing: {batch_file}
2. Track new URLs in: {url_log_file}
3. Update LAST_PROCESSED={idx} in progress_tracker.txt when done
4. Say only: "Done #{idx}"
"""
    else:
        # Fresh start
        prompt = f"""Process university #{idx}: {uni['University Name']}
URL: {uni['URL']}

STEPS:
1. Navigate to URL
2. IMMEDIATELY write this URL to: {url_log_file}
3. Search for trombone faculty
4. For EVERY new page/URL you visit, append it to: {url_log_file}
   (One URL per line - this creates a trail of your search)
5. Write results to: {batch_file}
   Headers: University,Faculty Name,Title,Email,Phone,Profile URL,Notes
6. Update LAST_PROCESSED={idx} in progress_tracker.txt
7. Say only: "Done #{idx}"

IMPORTANT: Track ALL URLs visited in {url_log_file}
If NO trombone faculty: write to results/no_trombone_found.csv
Try /faculty or /music if main search fails."""
    
    return prompt

if __name__ == "__main__":
    prompt = generate_prompt()
    
    # Save to file for Claude Desktop
    with open("current_prompt.txt", "w") as f:
        f.write(prompt)
    
    print("Prompt saved to current_prompt.txt")