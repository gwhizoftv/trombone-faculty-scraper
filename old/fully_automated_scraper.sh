#!/bin/bash
# Fully automated scraping with auto-kill after timeout

echo "Starting FULLY AUTOMATED trombone faculty scraping"
echo "=================================================="

# Configuration
TIMEOUT_MINUTES=5  # Kill Claude after 5 minutes per batch
UNIVERSITIES_PER_BATCH=2

# Initialize if needed
if [ ! -f progress_tracker.txt ]; then
    echo "LAST_PROCESSED=0" > progress_tracker.txt
    echo "TOTAL_UNIVERSITIES=202" >> progress_tracker.txt
fi

while true; do
    # Read current progress
    LAST=$(grep LAST_PROCESSED progress_tracker.txt | cut -d'=' -f2)
    TOTAL=$(grep TOTAL_UNIVERSITIES progress_tracker.txt | cut -d'=' -f2)
    
    if [ "$LAST" -ge "$TOTAL" ]; then
        echo "All universities processed!"
        break
    fi
    
    echo ""
    echo "Progress: $LAST / $TOTAL universities completed"
    echo "Processing next $UNIVERSITIES_PER_BATCH universities..."
    
    # Generate prompt for next batch
    python3 generate_prompt.py
    
    # Copy prompt to clipboard
    cat current_prompt.txt | pbcopy
    
    echo "Launching Claude Desktop..."
    echo "Will auto-kill after $TIMEOUT_MINUTES minutes"
    
    # Launch Claude Desktop in background
    open /Applications/Claude.app &
    CLAUDE_PID=$!
    
    # Wait for Claude to fully launch (adjust if needed)
    sleep 5
    
    # Use AppleScript to paste the prompt automatically
    osascript <<EOF
tell application "Claude" to activate
delay 1
tell application "System Events"
    keystroke "v" using command down
    delay 0.5
    keystroke return
end tell
EOF
    
    echo "Claude is processing universities..."
    echo "Timer: $TIMEOUT_MINUTES minutes"
    
    # Wait for timeout
    sleep $((TIMEOUT_MINUTES * 60))
    
    echo "Timeout reached, killing Claude Desktop..."
    
    # Kill Claude Desktop
    pkill -x "Claude"
    
    # Wait a moment for clean shutdown
    sleep 3
    
    # Update progress (assume 2 universities were processed)
    NEW_LAST=$((LAST + UNIVERSITIES_PER_BATCH))
    sed -i '' "s/LAST_PROCESSED=.*/LAST_PROCESSED=$NEW_LAST/" progress_tracker.txt
    
    echo "Batch complete. Waiting 5 seconds before next batch..."
    sleep 5
done

echo ""
echo "=================================================="
echo "All scraping complete!"
echo "Results saved in: trombone_faculty_results.csv"