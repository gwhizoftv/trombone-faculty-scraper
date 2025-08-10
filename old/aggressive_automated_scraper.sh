#!/bin/bash
# Aggressive automated scraping - kills Claude more reliably

echo "Starting AGGRESSIVE AUTOMATED trombone faculty scraping"
echo "======================================================"

# Configuration
TIMEOUT_MINUTES=4  # Kill Claude after 4 minutes (should be enough for 2 universities)

# Initialize if needed
if [ ! -f progress_tracker.txt ]; then
    echo "LAST_PROCESSED=0" > progress_tracker.txt
    echo "TOTAL_UNIVERSITIES=202" >> progress_tracker.txt
fi

# Function to kill Claude Desktop completely
kill_claude() {
    echo "Killing Claude Desktop..."
    
    # Try graceful kill first
    pkill -x "Claude"
    sleep 2
    
    # Force kill if still running
    if pgrep -x "Claude" > /dev/null; then
        echo "Force killing Claude..."
        pkill -9 -x "Claude"
    fi
    
    # Also kill any helper processes
    pkill -f "Claude Helper"
    pkill -f "Claude.app"
    
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
    
    # Generate prompt
    python3 generate_prompt.py
    
    # Get prompt content
    PROMPT=$(<current_prompt.txt)
    
    echo "Starting batch..."
    echo "Timeout: $TIMEOUT_MINUTES minutes"
    
    # Launch Claude with environment
    source launch_claude_with_env.sh &
    
    # Wait for Claude to launch
    sleep 8
    
    # Auto-paste prompt using AppleScript
    osascript <<EOF
tell application "Claude"
    activate
end tell
delay 2
tell application "System Events"
    -- Create new conversation
    keystroke "n" using command down
    delay 1
    
    -- Paste the prompt
    set the clipboard to "$PROMPT"
    keystroke "v" using command down
    delay 0.5
    
    -- Send the message
    keystroke return
end tell
EOF
    
    # Let Claude work for the timeout period
    echo "Claude is working..."
    
    # Show countdown
    for ((i=$TIMEOUT_MINUTES; i>0; i--)); do
        echo "  Time remaining: $i minutes"
        sleep 60
    done
    
    # Kill Claude
    kill_claude
    
    # Update progress
    NEW_LAST=$((LAST + 2))
    sed -i '' "s/LAST_PROCESSED=.*/LAST_PROCESSED=$NEW_LAST/" progress_tracker.txt
    
    echo "Batch complete. Waiting 5 seconds..."
    sleep 5
done

echo ""
echo "======================================================"
echo "SCRAPING COMPLETE!"
echo "Results in: trombone_faculty_results.csv"