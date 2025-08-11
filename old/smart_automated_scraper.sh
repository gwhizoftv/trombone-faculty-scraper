#!/bin/bash
# Smart automated scraping - kills Claude after detecting 2 universities completed

# Setup logging
LOG_DIR="logs"
BATCH_DIR="results/batches"
TMP_DIR="tmp"
mkdir -p "$LOG_DIR"
mkdir -p "$BATCH_DIR"
mkdir -p "$TMP_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/scraper_${TIMESTAMP}.log"

# Function to log to both file and terminal
log_message() {
    echo "$1" | tee -a "$LOG_FILE"
}

log_message "Starting SMART AUTOMATED trombone faculty scraping"
log_message "Log file: $LOG_FILE"
log_message "=================================================="

# Configuration
UNIVERSITIES_PER_BATCH=1  # One at a time to avoid conversation limits
MAX_WAIT_MINUTES=5   # Shorter timeout since just one university

# Initialize if needed
if [ ! -f progress_tracker.txt ]; then
    echo "LAST_PROCESSED=0" > progress_tracker.txt
    echo "TOTAL_UNIVERSITIES=202" >> progress_tracker.txt
fi

# No need for a main output file - we'll merge batch files later

# Function to kill Claude Desktop
kill_claude() {
    log_message "Stopping Claude Desktop..."
    # Kill all Claude processes forcefully
    pkill -9 -x "Claude" 2>/dev/null
    pkill -9 -f "Claude Helper" 2>/dev/null
    sleep 1
    
    # Double-check and force kill if still running
    if pgrep -x "Claude" > /dev/null; then
        log_message "Claude still running, force killing ALL instances..."
        killall -9 Claude 2>/dev/null
        sleep 1
    fi
}

RETRY_COUNT=0
MAX_RETRIES=3

while true; do
    # Read current progress
    LAST=$(grep LAST_PROCESSED progress_tracker.txt | cut -d'=' -f2 | tr -d ' ')
    TOTAL=$(grep TOTAL_UNIVERSITIES progress_tracker.txt | cut -d'=' -f2 | tr -d ' ')
    
    # Default TOTAL if not found
    if [ -z "$TOTAL" ]; then
        TOTAL=202
        echo "TOTAL_UNIVERSITIES=202" >> progress_tracker.txt
        log_message "Added missing TOTAL_UNIVERSITIES to progress_tracker.txt"
    fi
    
    if [ "$LAST" -ge "$TOTAL" ]; then
        log_message "All universities processed!"
        break
    fi
    
    log_message ""
    log_message "=========================================="
    log_message "Progress: $LAST / $TOTAL universities"
    log_message "=========================================="
    
    # Only kill Claude if it's still running from a previous failed run
    if pgrep -x "Claude" > /dev/null; then
        log_message "Claude still running from previous session, stopping..."
        kill_claude
    fi
    
    # Determine which batch file to monitor
    NEXT_START=$((LAST + 1))
    BATCH_FILE=$(printf "results/batches/uni_%03d.csv" $NEXT_START)
    log_message "Will monitor for file: $BATCH_FILE"
    
    # Generate prompt for next university (single) - with resume capability
    python3 generate_single_prompt_with_resume.py
    
    # Get prompt content
    PROMPT=$(<current_prompt.txt)
    
    # Save prompt to logs for debugging
    echo "$PROMPT" > "$LOG_DIR/prompt_batch_${LAST}.txt"
    
    log_message "Starting university #$NEXT_START..."
    log_message "Processing single university to avoid conversation limits..."
    
    # Make absolutely sure no Claude is running before starting
    killall -9 Claude 2>/dev/null
    sleep 1
    
    # Launch Claude directly (without nvm issues)
    open -F /Applications/Claude.app  # -F opens fresh instance
    
    # Wait for Claude to launch
    log_message "Waiting for Claude to launch..."
    sleep 3
    
    # Ensure Claude is the active application and frontmost
    osascript -e 'tell application "Claude" to activate'
    osascript -e 'tell application "System Events" to set frontmost of process "Claude" to true'
    sleep 1
    
    # Wait for Claude window to be ready
    WINDOW_CHECK=$(osascript -e '
        tell application "System Events"
            repeat 10 times
                if exists window 1 of process "Claude" then
                    return "Window exists"
                end if
                delay 1
            end repeat
            return "No window found"
        end tell
    ')
    log_message "Claude window check: $WINDOW_CHECK"
    
    # Copy prompt to clipboard
    cat current_prompt.txt | pbcopy
    log_message "Prompt copied to clipboard"
    
    # Verify clipboard content
    CLIPBOARD_CHECK=$(pbpaste | head -1)
    log_message "First line of clipboard: $CLIPBOARD_CHECK"
    
    # Create new conversation and paste prompt
    osascript -e '
        tell application "System Events"
            tell process "Claude"
                -- Create new conversation
                keystroke "n" using command down
                delay 0.5
                
                -- Paste the prompt
                keystroke "v" using command down
                delay 0.3
                
                -- Send the message
                keystroke return
            end tell
        end tell
    '
    
    # Take a screenshot for debugging after 10 seconds
    sleep 10
    screencapture -x "debug_screenshots/claude_$(date +%Y%m%d_%H%M%S).png"
    log_message "Screenshot saved to debug_screenshots/"
    
    log_message "Claude is working..."
    log_message "Monitoring for batch file: $BATCH_FILE"
    
    # Monitor for completion - check for batch file creation and progress tracker
    SECONDS_WAITED=0
    MAX_SECONDS=180  # 3 minutes should be enough for one university
    
    while [ $SECONDS_WAITED -lt $MAX_SECONDS ]; do
        # Check if batch file was created
        BATCH_EXISTS=0
        if [ -f "$BATCH_FILE" ]; then
            BATCH_EXISTS=1
        fi
        
        # Also check if progress_tracker.txt was updated (re-read each time)
        CURRENT_PROGRESS=$(grep LAST_PROCESSED progress_tracker.txt | cut -d'=' -f2 | tr -d ' ')
        PROGRESS_CHANGED=$((CURRENT_PROGRESS - LAST))
        
        # Success if either condition is met
        if [ $BATCH_EXISTS -eq 1 ] || [ $PROGRESS_CHANGED -ge $UNIVERSITIES_PER_BATCH ]; then
            log_message ""
            log_message "SUCCESS: Batch completed!"
            log_message "Batch file created: $BATCH_EXISTS"
            log_message "Progress: Advanced by $PROGRESS_CHANGED"
            break
        fi
        
        # Check for "BATCH COMPLETE" message in Claude output (if visible)
        if pgrep -x "Claude" > /dev/null; then
            # Claude is still running
            :
        else
            log_message "Claude appears to have stopped - checking results..."
            break
        fi
        
        # Show progress every 15 seconds
        if [ $((SECONDS_WAITED % 15)) -eq 0 ] && [ $SECONDS_WAITED -gt 0 ]; then
            log_message "  Status: Batch file=$BATCH_EXISTS, Progress=$PROGRESS_CHANGED (${SECONDS_WAITED}s elapsed)"
        fi
        
        sleep 1
        SECONDS_WAITED=$((SECONDS_WAITED + 1))
    done
    
    if [ $SECONDS_WAITED -ge $MAX_SECONDS ]; then
        log_message "WARNING: Timeout after 3 minutes - Claude may have hit conversation limit"
        
        # Check if incomplete marker exists - means Claude was working but timed out
        if [ -f "$TMP_DIR/incomplete_university.json" ]; then
            log_message "DETECTED: Incomplete university processing - will resume on next run"
            
            # Check if URL log exists to see progress
            URL_LOG="$TMP_DIR/uni_$(printf '%03d' $NEXT_START)_urls.txt"
            if [ -f "$URL_LOG" ]; then
                URLS_VISITED=$(wc -l < "$URL_LOG" | tr -d ' ')
                log_message "URLs visited before timeout: $URLS_VISITED"
                LAST_URL=$(tail -1 "$URL_LOG")
                log_message "Last URL visited: $LAST_URL"
                
                # Update incomplete marker with last URL
                python3 -c "import json; 
                with open('$TMP_DIR/incomplete_university.json', 'r') as f: data = json.load(f);
                data['last_url_visited'] = '$LAST_URL';
                with open('$TMP_DIR/incomplete_university.json', 'w') as f: json.dump(data, f)"
            fi
        fi
    fi
    
    # Kill Claude
    kill_claude
    
    # Check if batch file exists even if incomplete
    if [ -f "$BATCH_FILE" ]; then
        log_message "Batch file was created: $BATCH_FILE"
        LINES=$(wc -l < "$BATCH_FILE" | tr -d ' ')
        log_message "Batch file has $LINES lines"
        if [ $LINES -eq 1 ]; then
            log_message "WARNING: Batch file only has header - no faculty found?"
        elif [ $LINES -eq 0 ]; then
            log_message "WARNING: Batch file is empty!"
        fi
    else
        log_message "WARNING: Batch file was NOT created - may need to retry"
    fi
    
    # Check final state by looking at batch file
    FINAL_PROGRESS=$(grep LAST_PROCESSED progress_tracker.txt | cut -d'=' -f2)
    
    # Check if incomplete marker was removed (means Claude finished successfully)
    if [ ! -f "$TMP_DIR/incomplete_university.json" ]; then
        log_message "University completed successfully (incomplete marker removed)"
    else
        log_message "University may be incomplete - will resume on next iteration"
        # Don't update progress if incomplete
        continue
    fi
    
    # If progress tracker was already updated by Claude, use that
    if [ $FINAL_PROGRESS -gt $LAST ]; then
        log_message "Progress already updated by Claude: $LAST -> $FINAL_PROGRESS"
    elif [ -f "$BATCH_FILE" ]; then
        # Batch file exists, assume success and update progress
        NEW_LAST=$((LAST + 1))
        sed -i '' "s/LAST_PROCESSED=.*/LAST_PROCESSED=$NEW_LAST/" progress_tracker.txt
        log_message "Updated progress - batch file created"
    else
        log_message "Warning: No batch file created - may need manual check"
        # Don't auto-skip, let user decide
    fi
    
    log_message "Waiting 2 seconds before next batch..."
    sleep 2
done

log_message ""
log_message "=================================================="
log_message "SCRAPING COMPLETE!"
log_message "Batch files in: $BATCH_DIR"
log_message "Run ./merge_batches.sh to combine all results"
log_message "Check logs in: $LOG_DIR"