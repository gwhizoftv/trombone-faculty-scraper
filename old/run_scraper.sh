#!/bin/bash

echo "========================================="
echo "TROMBONE FACULTY SCRAPER"
echo "========================================="
echo ""
echo "This will open a browser and search for trombone faculty"
echo "at each university website."
echo ""
echo "Choose an option:"
echo "1) Test with Berklee only"
echo "2) Test with first 3 schools"
echo "3) Run on conservatories only (13 schools)"
echo "4) Run on all schools (202 schools)"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo "Testing with Berklee..."
        python3 -c "
import asyncio
from visual_scraper import VisualTromboneScraper

async def test_berklee():
    scraper = VisualTromboneScraper()
    await scraper.setup()
    await scraper.scrape_university('Berklee College of Music', 'https://berklee.edu')
    await scraper.cleanup()
    print('Test complete!')

asyncio.run(test_berklee())
"
        ;;
    2)
        echo "Testing with first 3 schools..."
        head -4 music_schools_wikipedia.csv > test_3_schools.csv
        python3 visual_scraper.py test_3_schools.csv
        ;;
    3)
        echo "Running on conservatories..."
        python3 visual_scraper.py conservatories_only.csv
        ;;
    4)
        echo "Running on all schools..."
        python3 visual_scraper.py music_schools_wikipedia.csv
        ;;
    *)
        echo "Invalid choice"
        ;;
esac