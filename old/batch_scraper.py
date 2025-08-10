#!/usr/bin/env python3
"""
Batch processor that runs single_university_scraper.py for a range of universities.
Processes them one at a time to avoid context issues.
"""

import subprocess
import sys
import time
from pathlib import Path

def main():
    if len(sys.argv) < 3:
        print("Usage: python batch_scraper.py <start_row> <end_row>")
        print("Example: python batch_scraper.py 1 5")
        print("\nThis will process universities from row start to end")
        sys.exit(1)
    
    start = int(sys.argv[1])
    end = int(sys.argv[2])
    
    print(f"BATCH PROCESSING UNIVERSITIES {start} to {end}")
    print("="*60)
    
    for i in range(start, end + 1):
        print(f"\n[{i}/{end}] Starting university #{i}")
        print("-"*40)
        
        # Tell Claude Desktop to run the single scraper
        print(f"\nCLAUDE: Please run this command and complete the scraping:")
        print(f"python single_university_scraper.py {i}")
        print("\nThen process the next one automatically.")
        
        # Give time between universities
        if i < end:
            print(f"\nAfter completing #{i}, continue with #{i+1}")
            time.sleep(2)
    
    print("\n" + "="*60)
    print("BATCH COMPLETE!")
    print(f"Processed universities {start} to {end}")
    print(f"Results saved to: trombone_faculty_results.csv")

if __name__ == "__main__":
    main()