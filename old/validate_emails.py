#!/usr/bin/env python3
"""
Email validation script using multiple non-intrusive techniques
"""

import csv
import re
import socket
import smtplib
import dns.resolver
from datetime import datetime
from collections import defaultdict
import time

class EmailValidator:
    def __init__(self):
        self.results = []
        
    def validate_syntax(self, email):
        """Check if email syntax is valid"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def check_mx_records(self, domain):
        """Check if domain has valid MX records"""
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            return len(mx_records) > 0, [str(mx.exchange) for mx in mx_records]
        except Exception as e:
            return False, []
    
    def smtp_verify(self, email, mx_host, timeout=10):
        """
        Careful SMTP verification - connects but doesn't send
        Some servers block this, so we handle gracefully
        """
        try:
            # Create SMTP connection
            server = smtplib.SMTP(timeout=timeout)
            server.set_debuglevel(0)  # Set to 1 for debugging
            
            # Connect to MX server
            server.connect(mx_host, 25)
            server.helo(server.local_hostname)
            
            # Try VRFY command (often disabled)
            code, message = server.verify(email)
            if code == 250:
                server.quit()
                return 'valid', 'VRFY confirmed'
            
            # Try RCPT TO (more reliable but still careful)
            server.mail('test@example.com')
            code, message = server.rcpt(email)
            server.quit()
            
            if code == 250:
                return 'valid', 'RCPT accepted'
            elif code == 550:
                return 'invalid', 'User does not exist'
            else:
                return 'unknown', f'Response code: {code}'
                
        except smtplib.SMTPServerDisconnected:
            return 'unknown', 'Server disconnected'
        except smtplib.SMTPConnectError:
            return 'unknown', 'Could not connect'
        except socket.timeout:
            return 'unknown', 'Connection timeout'
        except Exception as e:
            return 'unknown', str(e)[:50]
    
    def validate_email(self, email, smtp_check=False):
        """Complete validation process"""
        result = {
            'email': email,
            'syntax_valid': False,
            'domain': '',
            'mx_exists': False,
            'mx_servers': [],
            'smtp_status': 'not_checked',
            'smtp_details': '',
            'likely_valid': False
        }
        
        # Step 1: Syntax check
        if not self.validate_syntax(email):
            result['likely_valid'] = False
            return result
        
        result['syntax_valid'] = True
        
        # Step 2: Extract domain
        domain = email.split('@')[1]
        result['domain'] = domain
        
        # Step 3: Check MX records
        mx_exists, mx_servers = self.check_mx_records(domain)
        result['mx_exists'] = mx_exists
        result['mx_servers'] = mx_servers[:3]  # Keep first 3
        
        if not mx_exists:
            result['likely_valid'] = False
            return result
        
        # Step 4: Optional SMTP check (use carefully)
        if smtp_check and mx_servers:
            # Only check first MX server
            status, details = self.smtp_verify(email, mx_servers[0].rstrip('.'))
            result['smtp_status'] = status
            result['smtp_details'] = details
            
            # Small delay to be respectful
            time.sleep(0.5)
        
        # Determine likely validity
        if result['mx_exists']:
            if result['smtp_status'] == 'valid':
                result['likely_valid'] = True
            elif result['smtp_status'] == 'invalid':
                result['likely_valid'] = False
            else:
                # MX exists but SMTP unknown - probably valid
                result['likely_valid'] = True
        
        return result

def validate_faculty_emails():
    """Validate emails from the master file"""
    
    validator = EmailValidator()
    master_file = "trombone_faculty_master_FINAL_20250811.csv"
    
    print("Reading master file...")
    emails_to_validate = []
    
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get('Email', '').strip()
            if email and '@' in email:
                emails_to_validate.append({
                    'email': email,
                    'name': row.get('Faculty Name', ''),
                    'university': row.get('University', '')
                })
    
    print(f"Found {len(emails_to_validate)} emails to validate")
    print("\nValidating emails (this may take a few minutes)...")
    print("=" * 60)
    
    results = []
    stats = defaultdict(int)
    
    # Group by domain to be more efficient
    domains = defaultdict(list)
    for item in emails_to_validate:
        domain = item['email'].split('@')[1]
        domains[domain].append(item)
    
    print(f"Checking {len(domains)} unique domains...")
    
    for domain, items in domains.items():
        print(f"\nChecking {domain} ({len(items)} emails)...")
        
        # For common providers, we know they're good
        if domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
            for item in items:
                result = validator.validate_email(item['email'], smtp_check=False)
                result['name'] = item['name']
                result['university'] = item['university']
                results.append(result)
                stats['likely_valid'] += 1
                print(f"  ✓ {item['email']} - Known provider")
        else:
            # For .edu and other domains, check MX records
            # Only do SMTP check for a sample (first one) to avoid being blocked
            for i, item in enumerate(items):
                # Only SMTP check the first email per domain
                smtp_check = (i == 0 and domain.endswith('.edu'))
                
                result = validator.validate_email(item['email'], smtp_check=smtp_check)
                result['name'] = item['name']
                result['university'] = item['university']
                results.append(result)
                
                if result['likely_valid']:
                    stats['likely_valid'] += 1
                    print(f"  ✓ {item['email']}")
                else:
                    stats['likely_invalid'] += 1
                    print(f"  ✗ {item['email']} - {result.get('smtp_details', 'Invalid')}")
    
    # Write results to CSV
    output_file = f"email_validation_results_{datetime.now().strftime('%Y%m%d')}.csv"
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['email', 'name', 'university', 'likely_valid', 'syntax_valid', 
                     'domain', 'mx_exists', 'smtp_status', 'smtp_details']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total emails checked: {len(results)}")
    print(f"Likely VALID: {stats['likely_valid']}")
    print(f"Likely INVALID: {stats['likely_invalid']}")
    print(f"Validity rate: {stats['likely_valid']*100/len(results):.1f}%")
    
    print(f"\nDetailed results saved to: {output_file}")
    
    # Create list of invalid emails for review
    invalid_emails = [r for r in results if not r['likely_valid']]
    if invalid_emails:
        invalid_file = f"emails_needing_review_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(invalid_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(invalid_emails)
        print(f"Emails needing review: {invalid_file}")

if __name__ == "__main__":
    # Check if required library is installed
    try:
        import dns.resolver
    except ImportError:
        print("Installing required library: dnspython")
        import subprocess
        subprocess.check_call(['pip', 'install', 'dnspython'])
        import dns.resolver
    
    validate_faculty_emails()