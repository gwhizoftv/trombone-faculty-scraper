#!/bin/bash
# Universal setup script for any instrument faculty search
# Usage: ./setup_instrument_search.sh <instrument>
# Example: ./setup_instrument_search.sh flute

if [ $# -eq 0 ]; then
    echo "Usage: $0 <instrument>"
    echo "Example: $0 flute"
    echo "Example: $0 violin"
    echo "Example: $0 percussion"
    exit 1
fi

INSTRUMENT="$1"
INSTRUMENT_LOWER=$(echo "$INSTRUMENT" | tr '[:upper:]' '[:lower:]')
INSTRUMENT_UPPER=$(echo "$INSTRUMENT" | tr '[:lower:]' '[:upper:]')
INSTRUMENT_TITLE=$(echo "$INSTRUMENT" | awk '{print toupper(substr($0,1,1)) tolower(substr($0,2))}')

FOLDER_NAME="${INSTRUMENT_LOWER}-faculty"

echo "Setting up $INSTRUMENT_TITLE faculty search environment..."
echo "Creating folder: $FOLDER_NAME"

# Create the instrument folder
mkdir -p "$FOLDER_NAME"

# Copy necessary scripts (they already use relative paths now)
echo "Copying scripts..."
cp smart_automated_scraper_v2.sh "$FOLDER_NAME/"
cp generate_simple_resumable_prompt.py "$FOLDER_NAME/"
cp smart_email_finder.sh "$FOLDER_NAME/"
cp generate_email_finder_prompt.py "$FOLDER_NAME/"
cp merge_with_urls.py "$FOLDER_NAME/"
cp merge_pass2_with_master.py "$FOLDER_NAME/"
cp quick_email_check.py "$FOLDER_NAME/"
cp identify_missing_emails.py "$FOLDER_NAME/" 2>/dev/null
cp music_schools_wikipedia.csv "$FOLDER_NAME/"

cd "$FOLDER_NAME"

# Create necessary directories
echo "Creating directory structure..."
mkdir -p results/batches
mkdir -p results/url_logs
mkdir -p logs
mkdir -p tmp
mkdir -p debug_screenshots

# Initialize progress tracker
echo "LAST_PROCESSED=0" > progress_tracker.txt
echo "TOTAL_UNIVERSITIES=202" >> progress_tracker.txt

echo "Updating scripts for $INSTRUMENT_TITLE faculty..."

# Update all Python and shell scripts using the variables we already have
for file in *.py *.sh; do
    if [ -f "$file" ]; then
        # Single sed command with multiple replacements using our variables
        sed -i '' \
            -e "s/trombone faculty/${INSTRUMENT_LOWER} faculty/g" \
            -e "s/\btrombone\b/${INSTRUMENT_LOWER}/g" \
            -e "s/\bTrombone\b/${INSTRUMENT_TITLE}/g" \
            -e "s/\bTROMBONE\b/${INSTRUMENT_UPPER}/g" \
            -e "s/SEARCH FOR TROMBONE:/SEARCH FOR ${INSTRUMENT_UPPER}:/g" \
            -e "s/no_trombone_found/no_${INSTRUMENT_LOWER}_found/g" \
            -e "s/trombone_faculty_master/${INSTRUMENT_LOWER}_faculty_master/g" \
            "$file"
    fi
done

echo ""
echo "=================================================="
echo "Setup complete for $INSTRUMENT_TITLE faculty search!"
echo "=================================================="
echo ""
echo "Folder created: $FOLDER_NAME/"
echo ""
echo "To start searching for $INSTRUMENT_LOWER faculty:"
echo "  cd $FOLDER_NAME"
echo "  ./smart_automated_scraper_v2.sh"
echo ""
echo "For second pass (finding missing emails):"
echo "  1. After first pass, run: python3 identify_missing_emails.py"
echo "  2. Then run: ./smart_email_finder.sh"
echo ""
echo "Note: Different instruments have varying numbers of faculty."
echo "Piano/violin typically have many (10-20+), while instruments"
echo "like tuba or harp may have fewer faculty per school."