#!/bin/bash
# Reset script to start scraping from beginning

echo "Resetting scraper to start from beginning..."

# Reset progress tracker
echo "LAST_PROCESSED=0" > progress_tracker.txt
echo "TOTAL_UNIVERSITIES=202" >> progress_tracker.txt
echo "✓ Reset progress tracker to 0"

# Create directories if they don't exist
mkdir -p results/batches
mkdir -p logs
mkdir -p tmp
echo "✓ Created results/batches/, logs/, and tmp/ directories"

# Move existing temp files to tmp directory
if ls temp_*.csv 1> /dev/null 2>&1; then
    mv temp_*.csv tmp/ 2>/dev/null
    echo "✓ Moved existing temp files to tmp/"
fi

# Clear any existing batch files (optional - comment out if you want to keep them)
# rm -f batches/batch_*.csv
# echo "✓ Cleared old batch files"

# Clear the no_trombone_found file but keep header
echo "University,Reason,Notes" > results/no_trombone_found.csv
echo "✓ Reset results/no_trombone_found.csv"

# Kill any running Claude instances
pkill -9 -x "Claude" 2>/dev/null
pkill -9 -f "Claude Helper" 2>/dev/null
echo "✓ Killed any running Claude instances"

echo ""
echo "Ready to start fresh!"
echo "Run: ./smart_automated_scraper.sh"