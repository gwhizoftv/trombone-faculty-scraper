#!/usr/bin/env python3
"""
Merge second pass email results with the original master file
"""

import csv
from datetime import datetime
from pathlib import Path

def merge_results():
    # Read original master file
    master_file = "violin_faculty_master_20250811.csv"
    print(f"Reading original master: {master_file}")
    
    master_data = []
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        master_data = list(reader)
    
    print(f"Original master has {len(master_data)} faculty entries")
    
    # Create lookup dictionary for quick updates
    # Key: (University, Faculty Name) -> row index
    master_lookup = {}
    for idx, row in enumerate(master_data):
        key = (row.get('University', '').strip(), row.get('Faculty Name', '').strip())
        master_lookup[key] = idx
    
    # Process all pass 2 files
    updates_made = 0
    new_entries = []
    
    for i in range(1, 32):
        pass2_file = Path(f"results/batches/email_pass2_{i:03d}.csv")
        if pass2_file.exists():
            with open(pass2_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    continue
                
                f.seek(0)
                reader = csv.DictReader(f)
                
                for row in reader:
                    uni = row.get('University', '').strip()
                    name = row.get('Faculty Name', '').strip()
                    email = row.get('Email', '').strip()
                    
                    if email and '@' in email:
                        key = (uni, name)
                        
                        if key in master_lookup:
                            # Update existing entry
                            idx = master_lookup[key]
                            old_email = master_data[idx].get('Email', '').strip()
                            
                            if not old_email or old_email in ['NO EMAIL FOUND - SKIP', 'Not found', '']:
                                master_data[idx]['Email'] = email
                                master_data[idx]['Notes'] = master_data[idx].get('Notes', '') + ' [Email found in pass 2]'
                                updates_made += 1
                                print(f"  Updated: {name} ({uni}) -> {email}")
                        else:
                            # This is a new entry not in original master (shouldn't happen but just in case)
                            new_entry = {
                                'University': uni,
                                'Faculty Name': name,
                                'Title': row.get('Title', ''),
                                'Email': email,
                                'Phone': row.get('Phone', ''),
                                'Profile URL': row.get('Profile URL', ''),
                                'Source URL': f"Pass 2 search",
                                'Notes': row.get('Notes', '') + ' [Added in pass 2]'
                            }
                            new_entries.append(new_entry)
                            print(f"  New entry: {name} ({uni}) -> {email}")
    
    # Add any new entries to master data
    master_data.extend(new_entries)
    
    # Write updated master file
    output_file = f"violin_faculty_master_FINAL_{datetime.now().strftime('%Y%m%d')}.csv"
    
    fieldnames = ['University', 'Faculty Name', 'Title', 'Email', 'Phone', 'Profile URL', 'Source URL', 'Notes']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in master_data:
            # Ensure all fields exist
            for field in fieldnames:
                if field not in row:
                    row[field] = ''
            writer.writerow(row)
    
    # Statistics
    print("\n" + "="*60)
    print("MERGE COMPLETE!")
    print("="*60)
    print(f"Updates made: {updates_made}")
    print(f"New entries added: {len(new_entries)}")
    print(f"Total faculty in final master: {len(master_data)}")
    
    # Count emails
    with_emails = [r for r in master_data if r.get('Email', '').strip() and '@' in r.get('Email', '')]
    without_emails = [r for r in master_data if not r.get('Email', '').strip() or '@' not in r.get('Email', '')]
    
    print(f"\nEmail Statistics:")
    print(f"  Faculty WITH emails: {len(with_emails)} ({len(with_emails)*100/len(master_data):.1f}%)")
    print(f"  Faculty WITHOUT emails: {len(without_emails)} ({len(without_emails)*100/len(master_data):.1f}%)")
    
    print(f"\nFinal master file: {output_file}")
    
    # Also create a file with just the ones still missing emails
    if without_emails:
        no_email_file = f"faculty_still_without_emails_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(no_email_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(without_emails)
        print(f"Faculty still without emails: {no_email_file}")
    
    return output_file

if __name__ == "__main__":
    merge_results()