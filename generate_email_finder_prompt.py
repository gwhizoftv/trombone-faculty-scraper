#!/usr/bin/env python3
"""
Generate prompts specifically for finding missing email addresses
"""

import csv
from pathlib import Path

def get_next_university():
    # Read progress
    progress_file = Path("email_finder_progress.txt")
    try:
        with open(progress_file, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 1 and '=' in lines[0]:
                last_processed = int(lines[0].split('=')[1].strip())
            else:
                last_processed = 0
    except:
        last_processed = 0
    
    # Read universities with missing emails
    universities_file = Path("universities_missing_emails.csv")
    with open(universities_file, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
    
    # Get next university
    if last_processed < len(reader):
        return last_processed + 1, reader[last_processed]
    
    return None, None

def generate_prompt():
    idx, uni = get_next_university()
    
    if not uni:
        return "ALL UNIVERSITIES WITH MISSING EMAILS PROCESSED!"
    
    # File paths
    batch_file = f"/Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/results/batches/email_pass2_{idx:03d}.csv"
    url_log_file = f"/Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/tmp/email_pass2_{idx:03d}_urls.txt"
    
    # Parse faculty names
    faculty_list = uni['Faculty_Names'].split('; ') if uni['Faculty_Names'] else []
    
    prompt = f"""EMAIL FINDING MISSION #{idx}: {uni['University Name']}
URL: {uni['URL']}

CRITICAL: Find email addresses for these {uni['Missing_Count']} faculty members:
{chr(10).join(f'- {name}' for name in faculty_list)}

DEEP SEARCH STRATEGY:

1. GOOGLE SEARCH FIRST for each faculty member:
   - Search: "[Faculty Name]" (full name in quotes)
   - Look for their personal website → Contact page
   - Check for social media profiles (Instagram @username often has email)
   - YouTube channel → Click "...more" in description for email (christoflur@gmail.com example)

2. COURSICLE.COM SEARCH (if site allows access):
   - Go to coursicle.com
   - Search for the university
   - Search for faculty name in the school's search
   - If profile appears, note the URL pattern
   - Try navigating directly to: coursicle.com/[university]/professors/[FirstName]+[LastName]
   - If blocked or fails, try Google: "site:coursicle.com [Faculty Name] [University]"
   - Look for email on the profile page (often shows email like cliftone@apsu.edu)

3. GOOGLE EMAIL PATTERN:
   - Search: "firstname.lastname@university.edu"
   - Try variations: first.last, flast, firstl, etc.
   - Look for the email in cached pages or PDFs

4. UNIVERSITY WEBSITE:
   - Navigate to main URL
   - Look for search bar in upper right - search faculty name
   - Try these specific pages:
     - /directory
     - /faculty-directory
     - /people
     - /contact
     - /faculty-staff
     - /music/faculty
     - /music/directory
     - /about/directory

5. SOCIAL MEDIA PROFILES:
   - Check Instagram bio (@chrishernacki example)
   - Facebook profile/page
   - Twitter/X bio
   - LinkedIn contact info

SAVE TO: {batch_file}
Headers: University,Faculty Name,Email,Phone,Notes
Track URLs in: {url_log_file}

IMPORTANT:
- ONLY save if you find a real email address
- If no email found after thorough search, note in file: "NO EMAIL FOUND after deep search"
- Update email_finder_progress.txt: LAST_PROCESSED={idx}
- Say only: "Done #{idx}"

This is a SECOND PASS - be extremely thorough!"""
    
    return prompt

if __name__ == "__main__":
    prompt = generate_prompt()
    
    # Save to file for Claude Desktop
    with open("current_prompt.txt", "w") as f:
        f.write(prompt)
    
    print("Email finder prompt saved to current_prompt.txt")