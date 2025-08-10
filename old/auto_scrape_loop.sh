#!/bin/bash
# Automated loop to process universities in batches of 2

echo "Starting automated trombone faculty scraping"
echo "=========================================="

# Check if Claude Desktop is already running
if pgrep -x "Claude" > /dev/null; then
    echo "ERROR: Claude Desktop is already running. Please quit it first."
    exit 1
fi

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
    echo "Generating prompt for next batch..."
    
    # Generate prompt for next 2 universities
    python3 generate_prompt.py
    
    echo "Launching Claude Desktop with prompt..."
    echo "----------------------------------------"
    
    # Copy prompt to clipboard (macOS)
    cat current_prompt.txt | pbcopy
    
    # Launch Claude Desktop with environment
    source launch_claude_with_env.sh
    
    echo ""
    echo "INSTRUCTIONS:"
    echo "1. Claude Desktop is opening..."
    echo "2. The prompt is already in your clipboard"
    echo "3. Press Cmd+V to paste the prompt"
    echo "4. Let Claude complete the 2 universities"
    echo "5. When you see 'BATCH COMPLETE', close Claude Desktop"
    echo "6. Press ENTER here to continue with next batch"
    echo ""
    read -p "Press ENTER after Claude completes the batch and you've closed it: "
    
    # Update progress from what Claude saved
    # (Claude should update progress_tracker.txt)
    
    echo "Waiting 3 seconds before next batch..."
    sleep 3
done

echo ""
echo "=========================================="
echo "Scraping complete!"
echo "Results saved in: trombone_faculty_results.csv"