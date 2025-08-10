#!/usr/bin/env python3
"""
Generates a prompt for Claude Desktop to process the next 2 universities
"""

import csv
from pathlib import Path

def get_next_universities():
    # Read progress
    progress_file = Path("progress_tracker.txt")
    with open(progress_file, 'r') as f:
        lines = f.readlines()
        last_processed = int(lines[0].split('=')[1].strip())
    
    # Read universities CSV
    universities_file = Path("music_schools_wikipedia.csv")
    with open(universities_file, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
    
    # Get next 2 universities with URLs
    next_unis = []
    start_idx = last_processed
    for i in range(start_idx, min(start_idx + 10, len(reader))):  # Check up to 10 ahead
        if reader[i]['URL']:
            next_unis.append((i + 1, reader[i]))  # Store 1-based index
            if len(next_unis) == 2:
                break
    
    return next_unis, last_processed

def generate_prompt():
    unis, last_processed = get_next_universities()
    
    if not unis:
        return "ALL UNIVERSITIES PROCESSED!"
    
    prompt = f"""Process these 2 universities for trombone faculty:

IMPORTANT: APPEND to existing trombone_faculty_results.csv - DO NOT overwrite!
Use @filesystem to read the existing file first, then APPEND new rows.

UNIVERSITY #{unis[0][0]}: {unis[0][1]['University Name']}
1. Navigate to {unis[0][1]['URL']}
2. Find search (check TOP-RIGHT corner first)
3. Search "trombone faculty" or "trombone professor"
4. Extract from each faculty: Name, Title, EMAIL (required), Phone
5. APPEND (don't overwrite!) to trombone_faculty_results.csv

"""
    
    if len(unis) > 1:
        prompt += f"""UNIVERSITY #{unis[1][0]}: {unis[1][1]['University Name']}
1. Navigate to {unis[1][1]['URL']}
2. Find search (check TOP-RIGHT corner first)
3. Search "trombone faculty" or "trombone professor"
4. Extract from each faculty: Name, Title, EMAIL (required), Phone
5. APPEND (don't overwrite!) to trombone_faculty_results.csv

"""
    
    prompt += f"""CRITICAL INSTRUCTIONS:
- APPEND to CSV - never overwrite the existing file!
- Read existing CSV first with @filesystem, then append new rows
- Be VERY BRIEF in responses to save context
- Focus on EMAIL extraction (required for each faculty)
- After completing these 2, write "{unis[-1][0]}" to progress_tracker.txt as LAST_PROCESSED value
- Then say "BATCH COMPLETE - Ready for next batch"

CSV Format: University,Faculty Name,Title,Email,Phone,Profile URL,Notes

If no search found in 10 seconds, try /faculty or /people URLs."""
    
    return prompt

if __name__ == "__main__":
    prompt = generate_prompt()
    
    # Save to file for Claude Desktop
    with open("current_prompt.txt", "w") as f:
        f.write(prompt)
    
    print("Prompt saved to current_prompt.txt")
    print("\n" + "="*60)
    print(prompt)