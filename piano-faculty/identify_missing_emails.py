#!/usr/bin/env python3
"""
Identify universities with faculty missing email addresses
and create a new CSV for targeted second pass
"""

import csv
from collections import defaultdict

def analyze_missing_emails():
    # Read the master file
    master_file = "piano_faculty_master_20250811.csv"
    
    # Track universities with missing emails
    missing_by_university = defaultdict(list)
    complete_by_university = defaultdict(list)
    
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            uni = row.get('University', '').strip()
            if not uni:  # Skip empty university names
                continue
                
            faculty_name = row.get('Faculty Name', '').strip()
            email = row.get('Email', '').strip()
            
            if not email or email in ['NO EMAIL FOUND - SKIP', 'Not found', 'Not provided']:
                missing_by_university[uni].append({
                    'name': faculty_name,
                    'title': row.get('Title', ''),
                    'profile_url': row.get('Profile URL', '')
                })
            else:
                complete_by_university[uni].append(faculty_name)
    
    # Create report
    print("=" * 60)
    print("UNIVERSITIES WITH MISSING EMAIL DATA")
    print("=" * 60)
    
    universities_to_retry = []
    
    for uni in sorted(missing_by_university.keys()):
        missing_count = len(missing_by_university[uni])
        complete_count = len(complete_by_university.get(uni, []))
        total = missing_count + complete_count
        
        print(f"\n{uni}")
        print(f"  Missing emails: {missing_count}/{total}")
        for faculty in missing_by_university[uni]:
            print(f"    - {faculty['name']}: {faculty['title']}")
        
        # Add to retry list
        universities_to_retry.append({
            'University Name': uni,
            'Missing_Count': missing_count,
            'Total_Faculty': total,
            'Faculty_Names': '; '.join([f['name'] for f in missing_by_university[uni]])
        })
    
    # Read original Wikipedia CSV to get URLs
    wiki_data = {}
    with open('music_schools_wikipedia.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            wiki_data[row['University Name']] = row['URL']
    
    # Create new CSV for universities needing email updates
    output_file = 'universities_missing_emails.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['University Name', 'URL', 'Missing_Count', 'Total_Faculty', 'Faculty_Names']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for uni_data in universities_to_retry:
            uni_name = uni_data['University Name']
            uni_data['URL'] = wiki_data.get(uni_name, '')
            writer.writerow(uni_data)
    
    print(f"\n{'=' * 60}")
    print(f"SUMMARY:")
    print(f"  Universities with missing emails: {len(missing_by_university)}")
    print(f"  Total faculty missing emails: {sum(len(v) for v in missing_by_university.values())}")
    print(f"\nCreated file: {output_file}")
    
    return universities_to_retry

if __name__ == "__main__":
    analyze_missing_emails()