#!/usr/bin/env python3
"""
Quick email validation focusing on syntax and MX records only
"""

import csv
import re
import dns.resolver
from datetime import datetime
from collections import defaultdict

def validate_syntax(email):
    """Check if email syntax is valid"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def check_mx_records(domain):
    """Check if domain has valid MX records"""
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        return True
    except:
        return False

def quick_validate():
    """Quick validation of emails"""
    
    master_file = "trombone_faculty_master_FINAL_20250811.csv"
    
    print("Reading master file...")
    emails = []
    
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get('Email', '').strip()
            if email and '@' in email:
                emails.append({
                    'email': email,
                    'name': row.get('Faculty Name', ''),
                    'university': row.get('University', '')
                })
    
    print(f"Checking {len(emails)} emails...")
    
    # Group by domain for efficiency
    domains_checked = {}
    results = []
    
    for item in emails:
        email = item['email']
        
        # Check syntax
        if not validate_syntax(email):
            results.append({**item, 'status': 'invalid_syntax'})
            continue
        
        domain = email.split('@')[1]
        
        # Check if we already validated this domain
        if domain not in domains_checked:
            # Common providers are always valid
            if domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 
                         'aol.com', 'icloud.com', 'me.com', 'mac.com']:
                domains_checked[domain] = True
            else:
                # Check MX records
                domains_checked[domain] = check_mx_records(domain)
        
        if domains_checked[domain]:
            results.append({**item, 'status': 'valid'})
        else:
            results.append({**item, 'status': 'no_mx_records'})
    
    # Summary
    valid = [r for r in results if r['status'] == 'valid']
    invalid = [r for r in results if r['status'] != 'valid']
    
    print("\n" + "=" * 60)
    print("QUICK VALIDATION RESULTS")
    print("=" * 60)
    print(f"Total emails: {len(results)}")
    print(f"Valid (syntax + MX): {len(valid)} ({len(valid)*100/len(results):.1f}%)")
    print(f"Invalid: {len(invalid)}")
    
    # Break down by domain
    domain_stats = defaultdict(lambda: {'valid': 0, 'invalid': 0})
    for r in results:
        domain = r['email'].split('@')[1]
        if r['status'] == 'valid':
            domain_stats[domain]['valid'] += 1
        else:
            domain_stats[domain]['invalid'] += 1
    
    print("\nTop domains:")
    for domain, stats in sorted(domain_stats.items(), 
                                key=lambda x: x[1]['valid'], reverse=True)[:10]:
        total = stats['valid'] + stats['invalid']
        print(f"  {domain}: {stats['valid']}/{total} valid")
    
    # Save results
    if invalid:
        print(f"\nEmails with issues ({len(invalid)}):")
        output_file = f"emails_with_issues_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['email', 'name', 'university', 'status'])
            writer.writeheader()
            for r in invalid:
                writer.writerow(r)
                print(f"  {r['email']} - {r['status']}")
        print(f"\nProblematic emails saved to: {output_file}")
    
    return valid, invalid

if __name__ == "__main__":
    quick_validate()