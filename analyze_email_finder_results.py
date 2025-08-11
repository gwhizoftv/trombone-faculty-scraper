#!/usr/bin/env python3
"""
Analyze results from email finder second pass
"""

import csv
import os
from pathlib import Path

def analyze_results():
    batch_dir = Path("results/batches")
    
    # Track what we found
    emails_found = []
    no_emails = []
    total_searched = 0
    
    # Read original missing emails list
    with open('universities_missing_emails.csv', 'r') as f:
        reader = list(csv.DictReader(f))
        original_missing = {}
        for row in reader:
            original_missing[row['University Name']] = {
                'count': int(row['Missing_Count']),
                'names': row['Faculty_Names'].split('; ')
            }
    
    # Check each email_pass2 file
    for i in range(1, 32):
        file_path = batch_dir / f"email_pass2_{i:03d}.csv"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    print(f"File {i:03d}: EMPTY")
                    continue
                    
                f.seek(0)
                reader = csv.DictReader(f)
                rows = list(reader)
                
                if rows:
                    for row in rows:
                        uni = row.get('University', '')
                        name = row.get('Faculty Name', '')
                        email = row.get('Email', '')
                        
                        if email and '@' in email:
                            emails_found.append({
                                'uni': uni,
                                'name': name,
                                'email': email
                            })
                            print(f"✓ FOUND: {name} ({uni}): {email}")
                        elif 'NO EMAIL' in str(row.get('Notes', '')).upper():
                            no_emails.append({
                                'uni': uni,
                                'name': name
                            })
                            print(f"✗ NOT FOUND: {name} ({uni})")
                else:
                    print(f"File {i:03d}: No data rows")
    
    # Summary
    print("\n" + "="*60)
    print("SECOND PASS RESULTS SUMMARY")
    print("="*60)
    print(f"Total universities processed: 31")
    print(f"Faculty originally missing emails: 62")
    print(f"New emails FOUND: {len(emails_found)}")
    print(f"Still missing after deep search: {len(no_emails)}")
    
    if emails_found:
        print(f"\nSuccess rate: {len(emails_found)}/62 = {len(emails_found)*100/62:.1f}%")
        
        print("\nNEW EMAILS FOUND:")
        for item in sorted(emails_found, key=lambda x: x['uni']):
            print(f"  {item['uni']}: {item['name']} - {item['email']}")
    
    return emails_found, no_emails

if __name__ == "__main__":
    analyze_results()