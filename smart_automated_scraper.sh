#!/bin/bash
# Smart automated scraping - kills Claude after detecting 2 universities completed

echo "Starting SMART AUTOMATED trombone faculty scraping"
echo "=================================================="

# Configuration
UNIVERSITIES_PER_BATCH=2
MAX_WAIT_MINUTES=10  # Safety timeout if nothing happens
OUTPUT_FILE="trombone_faculty_results.csv"

# Initialize if needed
if [ ! -f progress_tracker.txt ]; then
    echo "LAST_PROCESSED=0" > progress_tracker.txt
    echo "TOTAL_UNIVERSITIES=202" >> progress_tracker.txt
fi

# Create output file with headers if it doesn't exist
if [ ! -f "$OUTPUT_FILE" ]; then
    echo "University,Faculty Name,Title,Email,Phone,Profile URL,Notes" > "$OUTPUT_FILE"
fi

# Function to count universities in CSV
count_universities() {
    if [ -f "$OUTPUT_FILE" ]; then
        # Count unique university names (excluding header)
        tail -n +2 "$OUTPUT_FILE" | cut -d',' -f1 | sort -u | wc -l | tr -d ' '
    else
        echo "0"
    fi
}

# Function to kill Claude Desktop
kill_claude() {
    echo "Stopping Claude Desktop..."
    pkill -x "Claude"
    sleep 2
    if pgrep -x "Claude" > /dev/null; then
        pkill -9 -x "Claude"
    fi
    pkill -f "Claude Helper" 2>/dev/null
    sleep 2
}

while true; do
    # Read current progress
    LAST=$(grep LAST_PROCESSED progress_tracker.txt | cut -d'=' -f2)
    TOTAL=$(grep TOTAL_UNIVERSITIES progress_tracker.txt | cut -d'=' -f2)
    
    if [ "$LAST" -ge "$TOTAL" ]; then
        echo "All universities processed!"
        break
    fi
    
    echo ""
    echo "=========================================="
    echo "Progress: $LAST / $TOTAL universities"
    echo "=========================================="
    
    # Make sure Claude is not running
    kill_claude
    
    # Count universities before starting
    UNIS_BEFORE=$(count_universities)
    echo "Universities in CSV before: $UNIS_BEFORE"
    
    # Generate prompt for next batch
    python3 generate_prompt.py
    
    # Get prompt content
    PROMPT=$(<current_prompt.txt)
    
    echo "Starting new batch..."
    echo "Waiting for $UNIVERSITIES_PER_BATCH new universities in output..."
    
    # Launch Claude directly (without nvm issues)
    open /Applications/Claude.app
    
    # Wait for Claude to launch
    sleep 8
    
    # Copy prompt to clipboard first
    cat current_prompt.txt | pbcopy
    
    # Auto-paste prompt using simpler AppleScript
    osascript -e 'tell application "Claude" to activate'
    sleep 2
    osascript -e 'tell application "System Events" to keystroke "n" using command down'
    sleep 1
    osascript -e 'tell application "System Events" to keystroke "v" using command down'
    sleep 0.5
    osascript -e 'tell application "System Events" to keystroke return'
    
    echo "Claude is working..."
    echo "Monitoring $OUTPUT_FILE for new universities..."
    
    # Monitor for new universities
    SECONDS_WAITED=0
    MAX_SECONDS=$((MAX_WAIT_MINUTES * 60))
    
    while [ $SECONDS_WAITED -lt $MAX_SECONDS ]; do
        CURRENT_UNIS=$(count_universities)
        NEW_UNIS=$((CURRENT_UNIS - UNIS_BEFORE))
        
        if [ $NEW_UNIS -ge $UNIVERSITIES_PER_BATCH ]; then
            echo ""
            echo "SUCCESS: Added $NEW_UNIS new universities!"
            echo "Target of $UNIVERSITIES_PER_BATCH reached."
            break
        fi
        
        # Show progress every 30 seconds
        if [ $((SECONDS_WAITED % 30)) -eq 0 ] && [ $SECONDS_WAITED -gt 0 ]; then
            echo "  Status: $NEW_UNIS/$UNIVERSITIES_PER_BATCH universities completed (${SECONDS_WAITED}s elapsed)"
        fi
        
        sleep 5
        SECONDS_WAITED=$((SECONDS_WAITED + 5))
    done
    
    if [ $SECONDS_WAITED -ge $MAX_SECONDS ]; then
        echo "WARNING: Timeout after $MAX_WAIT_MINUTES minutes"
    fi
    
    # Kill Claude
    kill_claude
    
    # Update progress based on actual universities added
    FINAL_UNIS=$(count_universities)
    ACTUALLY_ADDED=$((FINAL_UNIS - UNIS_BEFORE))
    
    if [ $ACTUALLY_ADDED -gt 0 ]; then
        NEW_LAST=$((LAST + ACTUALLY_ADDED))
        sed -i '' "s/LAST_PROCESSED=.*/LAST_PROCESSED=$NEW_LAST/" progress_tracker.txt
        echo "Updated progress: $ACTUALLY_ADDED universities processed"
    else
        echo "No new universities added in this batch"
        # Skip the university if no faculty found
        NEW_LAST=$((LAST + 1))
        sed -i '' "s/LAST_PROCESSED=.*/LAST_PROCESSED=$NEW_LAST/" progress_tracker.txt
    fi
    
    echo "Waiting 5 seconds before next batch..."
    sleep 5
done

echo ""
echo "=================================================="
echo "SCRAPING COMPLETE!"
echo "Results in: $OUTPUT_FILE"
echo "Total universities with faculty: $(count_universities)"