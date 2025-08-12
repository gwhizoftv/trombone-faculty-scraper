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
    url_log_file = f"tmp/uni_{idx:03d}_urls.txt"
    batch_file = f"results/batches/uni_{idx:03d}.csv"
    
    if last_url:
        # Resume prompt
        prompt = f"""RESUMING university #{idx}: {uni['University Name']}

Last URL visited: {last_url}
Continue from there and find remaining trombone faculty.

CRITICAL: EMAIL ADDRESSES ARE REQUIRED!
- Only save faculty WITH email addresses
- Click into profile pages to find emails
- Check contact/directory pages
- If no email after thorough search, skip that person

RESUME STEPS:
1. APPEND to existing: {batch_file}
2. Track new URLs in: {url_log_file}
3. Search deeply for email addresses on:
   - Individual faculty pages
   - Department contact pages
   - Directory listings
4. Update progress_tracker.txt - REPLACE the entire file with exactly these 2 lines:
   LAST_PROCESSED={idx}
   TOTAL_UNIVERSITIES=202
5. Say only: "Done #{idx}"
"""
    else:
        # Fresh start
        prompt = f"""Process university #{idx}: {uni['University Name']}
URL: {uni['URL']}

CRITICAL: EMAIL ADDRESSES ARE REQUIRED - Without emails, the data is useless!

STEPS:
1. Navigate to URL
2. IMMEDIATELY write this URL to: {url_log_file}
3. SEARCH FOR TROMBONE:
   - First: Look for search bar (usually upper right of page) - type "trombone faculty"
   - If no search bar: Navigate to School of Music or Faculty pages
   - Click search results and explore thoroughly
4. For EACH faculty member found:
   - Click on their profile/bio page
   - Look for email on their individual page
   - Check faculty directory pages
   - Look for "contact" or "email" links
   - Check department contact pages
5. For EVERY new page/URL you visit, append it to: {url_log_file}
6. Write results to: {batch_file}
   Headers: University,Faculty Name,Title,Email,Phone,Profile URL,Notes
   
ESSENTIAL: 
- DO NOT save faculty without email addresses
- If no email found after checking profile, mark as "NO EMAIL FOUND - SKIP"
- Spend extra time searching for emails - they are often on separate contact pages

7. Update progress_tracker.txt - REPLACE the entire file with exactly these 2 lines:
   LAST_PROCESSED={idx}
   TOTAL_UNIVERSITIES=202
8. Say only: "Done #{idx}"

SEARCH PRIORITY:
1. Use search bar in upper right (type "trombone faculty")
2. Try /faculty, /music, /directory, /contact pages
3. School of Music page
4. Faculty directory
5. Music faculty list

If NO trombone faculty WITH EMAILS: write to results/no_trombone_found.csv"""
    
    return prompt

if __name__ == "__main__":
    prompt = generate_prompt()
    
    # Save to file for Claude Desktop
    with open("current_prompt.txt", "w") as f:
        f.write(prompt)
    
    print("Prompt saved to current_prompt.txt")