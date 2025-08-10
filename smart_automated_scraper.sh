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

# Create no-trombone tracking file if it doesn't exist
NO_TROMBONE_FILE="no_trombone_found.csv"
if [ ! -f "$NO_TROMBONE_FILE" ]; then
    echo "University,Reason,Notes" > "$NO_TROMBONE_FILE"
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
    log_message "Stopping Claude Desktop..."
    # Kill all Claude processes forcefully
    pkill -9 -x "Claude" 2>/dev/null
    pkill -9 -f "Claude Helper" 2>/dev/null
    sleep 3
    
    # Double-check and force kill if still running
    if pgrep -x "Claude" > /dev/null; then
        log_message "Claude still running, force killing ALL instances..."
        killall -9 Claude 2>/dev/null
        sleep 2
    fi
}

while true; do
    # Read current progress
    LAST=$(grep LAST_PROCESSED progress_tracker.txt | cut -d'=' -f2)
    TOTAL=$(grep TOTAL_UNIVERSITIES progress_tracker.txt | cut -d'=' -f2)
    
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
    
    # Generate prompt for next university (single)
    python3 generate_single_prompt.py
    
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
    sleep 6
    
    # Ensure Claude is the active application and frontmost
    osascript -e 'tell application "Claude" to activate'
    osascript -e 'tell application "System Events" to set frontmost of process "Claude" to true'
    sleep 3
    
    # Wait for Claude window to be ready
    osascript -e '
        tell application "System Events"
            repeat 10 times
                if exists window 1 of process "Claude" then
                    exit repeat
                end if
                delay 1
            end repeat
        end tell
    '
    
    # Copy prompt to clipboard
    cat current_prompt.txt | pbcopy
    log_message "Prompt copied to clipboard"
    
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
    
    log_message "Claude is working..."
    log_message "Monitoring for batch file: $BATCH_FILE"
    
    # Monitor for completion - check for batch file creation and progress tracker
    SECONDS_WAITED=0
    MAX_SECONDS=$((MAX_WAIT_MINUTES * 60))
    
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
        
        sleep 3
        SECONDS_WAITED=$((SECONDS_WAITED + 3))
    done
    
    if [ $SECONDS_WAITED -ge $MAX_SECONDS ]; then
        log_message "WARNING: Timeout after $MAX_WAIT_MINUTES minutes"
    fi
    
    # Kill Claude
    kill_claude
    
    # Check if batch file exists even if incomplete
    if [ -f "$BATCH_FILE" ]; then
        log_message "Batch file was created: $BATCH_FILE"
        LINES=$(wc -l < "$BATCH_FILE" | tr -d ' ')
        log_message "Batch file has $LINES lines"
        if [ $LINES -lt 2 ]; then
            log_message "WARNING: Batch file seems incomplete (only header?)"
        fi
    else
        log_message "WARNING: Batch file was NOT created - may need to retry"
    fi
    
    # Check final state
    FINAL_UNIS=$(count_universities)
    ACTUALLY_ADDED=$((FINAL_UNIS - UNIS_BEFORE))
    FINAL_PROGRESS=$(grep LAST_PROCESSED progress_tracker.txt | cut -d'=' -f2)
    
    # If progress tracker was already updated by Claude, use that
    if [ $FINAL_PROGRESS -gt $LAST ]; then
        log_message "Progress already updated by Claude: $LAST -> $FINAL_PROGRESS"
    elif [ $ACTUALLY_ADDED -gt 0 ]; then
        # Update based on CSV changes
        NEW_LAST=$((LAST + ACTUALLY_ADDED))
        sed -i '' "s/LAST_PROCESSED=.*/LAST_PROCESSED=$NEW_LAST/" progress_tracker.txt
        log_message "Updated progress based on CSV: $ACTUALLY_ADDED universities processed"
    else
        log_message "Warning: No progress detected - may need manual check"
        # Don't auto-skip, let user decide
    fi
    
    log_message "Waiting 5 seconds before next batch..."
    sleep 5
done

log_message ""
log_message "=================================================="
log_message "SCRAPING COMPLETE!"
log_message "Results in: $OUTPUT_FILE"
log_message "Total universities with faculty: $(count_universities)"
log_message "Check logs in: $LOG_DIR"