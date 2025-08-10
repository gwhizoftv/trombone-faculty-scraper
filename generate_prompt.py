#!/usr/bin/env python3
"""
Generates a prompt for Claude Desktop to process the next 2 universities
"""

import csv
from pathlib import Path

def get_next_universities():
    # Read progress
    progress_file = Path("progress_tracker.txt")
    try:
        with open(progress_file, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 1 and '=' in lines[0]:
                last_processed = int(lines[0].split('=')[1].strip())
            else:
                # Try to parse single number
                last_processed = int(lines[0].strip()) if lines else 0
    except (ValueError, IndexError):
        print("Warning: progress_tracker.txt format issue, resetting to 0")
        last_processed = 0
    
    # Read universities CSV
    universities_file = Path("music_schools_wikipedia.csv")
    with open(universities_file, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
    
    # Get next N universities with URLs (based on batch size)
    batch_size = 1  # Single university to avoid conversation limits
    next_unis = []
    start_idx = last_processed
    for i in range(start_idx, min(start_idx + 10, len(reader))):  # Check up to 10 ahead
        if reader[i]['URL']:
            next_unis.append((i + 1, reader[i]))  # Store 1-based index
            if len(next_unis) == batch_size:
                break
    
    return next_unis, last_processed

def generate_prompt():
    unis, last_processed = get_next_universities()
    
    if not unis:
        return "ALL UNIVERSITIES PROCESSED!"
    
    num_unis = len(unis)
    if num_unis == 1:
        prompt = f"""Process this university for trombone faculty:

IMPORTANT: Create a NEW CSV file for this batch:
/Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/results/batches/batch_{unis[0][0]:03d}_{unis[-1][0]:03d}.csv

Write ONLY this university to this NEW file with headers.
Each university gets its own file - we'll combine them later!

UNIVERSITY #{unis[0][0]}: {unis[0][1]['University Name']}
1. Navigate to {unis[0][1]['URL']}
2. QUICKLY click search icon (usually top-right) - don't wait
3. Type "trombone faculty" immediately when search opens
4. If on faculty page, use Cmd+F to search for: "trombone", "brass", "low brass"
5. SCROLL DOWN to check entire page - faculty may be listed below viewport
6. Extract: Name, Title, Email (check mailto: links!), Phone
7. If email not visible, click faculty profile link (accept "Open link" if warned)

"""
    
    if len(unis) > 1:
        prompt += f"""UNIVERSITY #{unis[1][0]}: {unis[1][1]['University Name']}
1. Navigate to {unis[1][1]['URL']}
2. QUICKLY click search icon (usually top-right) - don't wait
3. Type "trombone faculty" immediately when search opens
4. If on faculty page, use Cmd+F to search for: "trombone", "brass", "low brass"
5. SCROLL DOWN to check entire page - faculty may be listed below viewport
6. Extract: Name, Title, Email (check mailto: links!), Phone
7. If email not visible, click faculty profile link (accept "Open link" if warned)

"""
    
    prompt += f"""CRITICAL INSTRUCTIONS:
- MINIMIZE OUTPUT to avoid hitting conversation limits!
- NO tool explanations, NO narration, NO "I found...", NO "Let me..."
- Create NEW file batch_{unis[0][0]:03d}_{unis[-1][0]:03d}.csv for THIS batch only
- Include CSV headers in the new file
- Put ANY temporary files in: /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/tmp/
- Focus on EMAIL extraction (required for each faculty)

HANDLING NO TROMBONE FACULTY:
- If you find only general "Brass" faculty with no trombone mention, check if any teach low brass
- If NO trombone/low brass faculty found:
  1. Add to: /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/results/no_trombone_found.csv
  2. Still count as processed - continue to next university
  
- FIRST: Update status file when starting:
  /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/claude_status.txt
  Write: STATUS=WORKING\\nCURRENT_BATCH={unis[0][0]}-{unis[-1][0]}\\nMESSAGE=Processing
  
- After completing:
  1. Save a summary to: /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/logs/claude_batch_{unis[-1][0]}.txt
  2. Update progress_tracker.txt: /Volumes/8TB-SSD/TotalVU Dropbox/Michael Williams/Adrienne Albert Website/trombone marketing-claude1/progress_tracker.txt
     ONLY change the number: LAST_PROCESSED={unis[-1][0]}
  3. Update status: STATUS=COMPLETE\\nCURRENT_BATCH={unis[0][0]}-{unis[-1][0]}\\nMESSAGE=Done
  4. Say "BATCH COMPLETE - Ready for next batch"

CSV Format: University,Faculty Name,Title,Email,Phone,Profile URL,Notes
No-Trombone CSV Format: University,Reason,Notes

If no search found in 10 seconds, try /faculty or /people URLs."""
    
    return prompt

if __name__ == "__main__":
    prompt = generate_prompt()
    
    # Save to file for Claude Desktop
    with open("current_prompt.txt", "w") as f:
        f.write(prompt)
    
    print("Prompt saved to current_prompt.txt")