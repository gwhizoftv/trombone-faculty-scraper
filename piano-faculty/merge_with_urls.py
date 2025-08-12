#!/usr/bin/env python3
"""
Merge all batch CSV files into a master file, including the source URL for each university
"""

import csv
import os
from pathlib import Path
from datetime import datetime

def get_last_url_for_uni(uni_num):
    """Get the last URL visited for a university from its URL log"""
    # Check both permanent and temp locations
    url_log_paths = [
        f"results/url_logs/uni_{uni_num:03d}_urls.txt",
        f"tmp/uni_{uni_num:03d}_urls.txt"
    ]
    
    for path in url_log_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        # Return the last non-empty line
                        for line in reversed(lines):
                            url = line.strip()
                            if url and not url.startswith("No URL tracking"):
                                return url
            except Exception as e:
                print(f"Error reading URL log {path}: {e}")
    
    return "URL not logged"

def merge_batches():
    batch_dir = Path("results/batches")
    output_file = f"piano_faculty_master_{datetime.now().strftime('%Y%m%d')}.csv"
    
    # Collect all data
    all_faculty = []
    universities_processed = 0
    total_faculty = 0
    
    print("Merging batch files with source URLs...")
    print("=" * 60)
    
    # Process each batch file
    for batch_file in sorted(batch_dir.glob("uni_*.csv")):
        # Extract university number from filename
        uni_num = int(batch_file.stem.split('_')[1])
        
        # Get the last URL for this university
        source_url = get_last_url_for_uni(uni_num)
        
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                faculty_count = 0
                
                for row in reader:
                    # Clean up row - remove None keys
                    cleaned_row = {k: v for k, v in row.items() if k is not None}
                    
                    # Standardize field names
                    standardized = {}
                    standardized['University'] = cleaned_row.get('University', cleaned_row.get('Institution', ''))
                    standardized['Faculty Name'] = cleaned_row.get('Faculty Name', cleaned_row.get('Name', ''))
                    standardized['Title'] = cleaned_row.get('Title', '')
                    standardized['Email'] = cleaned_row.get('Email', '')
                    standardized['Phone'] = cleaned_row.get('Phone', '')
                    standardized['Profile URL'] = cleaned_row.get('Profile URL', cleaned_row.get('URL', ''))
                    standardized['Notes'] = cleaned_row.get('Notes', '')
                    standardized['Source URL'] = source_url
                    
                    all_faculty.append(standardized)
                    faculty_count += 1
                
                if faculty_count > 0:
                    universities_processed += 1
                    total_faculty += faculty_count
                    print(f"  {batch_file.name}: {faculty_count} faculty members - URL: {source_url[:50]}...")
                
        except Exception as e:
            print(f"  Error reading {batch_file.name}: {e}")
    
    # Write master file with new column order
    if all_faculty:
        fieldnames = ['University', 'Faculty Name', 'Title', 'Email', 'Phone', 'Profile URL', 'Source URL', 'Notes']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in all_faculty:
                # Ensure all fields exist
                for field in fieldnames:
                    if field not in row:
                        row[field] = ''
                writer.writerow(row)
        
        print("=" * 60)
        print(f"MERGE COMPLETE!")
        print(f"Universities with faculty: {universities_processed}")
        print(f"Total faculty found: {total_faculty}")
        print(f"Output file: {output_file}")
        
        # Also create a summary of faculty with emails
        with_emails = [f for f in all_faculty if f.get('Email', '').strip()]
        without_emails = [f for f in all_faculty if not f.get('Email', '').strip()]
        
        print(f"\nEmail Statistics:")
        print(f"  Faculty WITH emails: {len(with_emails)}")
        print(f"  Faculty WITHOUT emails: {len(without_emails)}")
        
        if without_emails:
            # Create a separate file for faculty without emails
            no_email_file = f"faculty_without_emails_{datetime.now().strftime('%Y%m%d')}.csv"
            with open(no_email_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(without_emails)
            print(f"  Faculty without emails saved to: {no_email_file}")
            
    else:
        print("No faculty data found to merge!")

if __name__ == "__main__":
    merge_batches()