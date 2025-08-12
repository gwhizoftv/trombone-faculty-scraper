#!/bin/bash
# Smart automated scraping V2 - with better resume logic

# Setup logging
LOG_DIR="logs"
BATCH_DIR="results/batches"
TMP_DIR="tmp"
URL_LOG_DIR="results/url_logs"
mkdir -p "$LOG_DIR"
mkdir -p "$BATCH_DIR"
mkdir -p "$TMP_DIR"
mkdir -p "$URL_LOG_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/scraper_${TIMESTAMP}.log"

# Function to log to both file and terminal
log_message() {
    echo "$1" | tee -a "$LOG_FILE"
}

log_message "Starting SMART AUTOMATED violin faculty scraping V2"
log_message "Log file: $LOG_FILE"
log_message "=================================================="

# Configuration
MAX_WAIT_MINUTES=3   # 3 minutes for one university

# Initialize if needed
if [ ! -f progress_tracker.txt ]; then
    echo "LAST_PROCESSED=0" > progress_tracker.txt
    echo "TOTAL_UNIVERSITIES=202" >> progress_tracker.txt
fi

# Function to kill Claude Desktop
kill_claude() {
    log_message "Stopping Claude Desktop..."
    pkill -9 -x "Claude" 2>/dev/null
    pkill -9 -f "Claude Helper" 2>/dev/null
    sleep 1
    
    if pgrep -x "Claude" > /dev/null; then
        killall -9 Claude 2>/dev/null
        sleep 1
    fi
}

while true; do
    # Read current progress
    LAST=$(grep LAST_PROCESSED progress_tracker.txt | cut -d'=' -f2 | tr -d ' ')
    TOTAL=$(grep TOTAL_UNIVERSITIES progress_tracker.txt | cut -d'=' -f2 | tr -d ' ')
    
    # Default TOTAL if not found
    if [ -z "$TOTAL" ]; then
        TOTAL=202
        echo "TOTAL_UNIVERSITIES=202" >> progress_tracker.txt
    fi
    
    if [ "$LAST" -ge "$TOTAL" ]; then
        log_message "All universities processed!"
        break
    fi
    
    log_message ""
    log_message "=========================================="
    log_message "Progress: $LAST / $TOTAL universities"
    log_message "=========================================="
    
    # Kill Claude if running
    if pgrep -x "Claude" > /dev/null; then
        log_message "Claude still running, stopping..."
        kill_claude
    fi
    
    # Determine which university to process
    NEXT_START=$((LAST + 1))
    BATCH_FILE="results/batches/uni_$(printf '%03d' $NEXT_START).csv"
    URL_LOG="tmp/uni_$(printf '%03d' $NEXT_START)_urls.txt"
    
    # Check if we're resuming or starting fresh
    if [ -f "$URL_LOG" ] && [ -s "$URL_LOG" ]; then
        log_message "Found existing URL log - RESUMING university #$NEXT_START"
        URLS_VISITED=$(wc -l < "$URL_LOG" | tr -d ' ')
        log_message "URLs already visited: $URLS_VISITED"
    else
        log_message "Starting FRESH for university #$NEXT_START"
    fi
    
    log_message "Will monitor for: $BATCH_FILE"
    
    # Generate prompt
    python3 generate_simple_resumable_prompt.py
    
    # Save prompt to logs
    cp current_prompt.txt "$LOG_DIR/prompt_batch_${NEXT_START}.txt"
    
    log_message "Processing university #$NEXT_START..."
    
    # Launch Claude
    open -F /Applications/Claude.app
    
    log_message "Waiting for Claude to launch..."
    sleep 3
    
    # Activate Claude
    osascript -e 'tell application "Claude" to activate'
    osascript -e 'tell application "System Events" to set frontmost of process "Claude" to true'
    sleep 1
    
    # Wait for window
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
    log_message "Claude window: $WINDOW_CHECK"
    
    # Copy and paste prompt
    cat current_prompt.txt | pbcopy
    log_message "Prompt copied to clipboard"
    
    # Create new conversation and paste
    osascript -e '
        tell application "System Events"
            tell process "Claude"
                keystroke "n" using command down
                delay 0.5
                keystroke "v" using command down
                delay 0.3
                keystroke return
            end tell
        end tell
    '
    
    # Screenshot for debugging
    sleep 10
    screencapture -x "debug_screenshots/claude_$(date +%Y%m%d_%H%M%S).png"
    
    log_message "Claude is working..."
    
    # Monitor for completion
    SECONDS_WAITED=0
    MAX_SECONDS=$((MAX_WAIT_MINUTES * 60))
    SUCCESS=0
    
    while [ $SECONDS_WAITED -lt $MAX_SECONDS ]; do
        # Check progress update
        CURRENT_PROGRESS=$(grep LAST_PROCESSED progress_tracker.txt | cut -d'=' -f2 | tr -d ' ')
        
        if [ "$CURRENT_PROGRESS" -gt "$LAST" ]; then
            log_message "SUCCESS: Progress updated to $CURRENT_PROGRESS"
            SUCCESS=1
            break
        fi
        
        # Check if batch file exists with content
        if [ -f "$BATCH_FILE" ]; then
            LINES=$(wc -l < "$BATCH_FILE" | tr -d ' ')
            if [ $LINES -gt 1 ]; then
                # Has header + at least one row
                log_message "Batch file has $LINES lines"
                
                # Also check if progress was supposed to be updated
                if [ ! -f "$URL_LOG" ] || [ ! -s "$URL_LOG" ]; then
                    # Fresh run with batch file = likely complete
                    log_message "Fresh run completed with batch file"
                    SUCCESS=1
                    # Update progress manually
                    sed -i '' "s/LAST_PROCESSED=.*/LAST_PROCESSED=$NEXT_START/" progress_tracker.txt
                    break
                fi
            fi
        fi
        
        # Progress indicator every 15 seconds
        if [ $((SECONDS_WAITED % 15)) -eq 0 ] && [ $SECONDS_WAITED -gt 0 ]; then
            log_message "  Waiting... (${SECONDS_WAITED}s elapsed)"
        fi
        
        sleep 1
        SECONDS_WAITED=$((SECONDS_WAITED + 1))
    done
    
    if [ $SECONDS_WAITED -ge $MAX_SECONDS ]; then
        log_message "TIMEOUT after $MAX_WAIT_MINUTES minutes"
        
        # Check if URL log exists - means we need to resume
        if [ -f "$URL_LOG" ] && [ -s "$URL_LOG" ]; then
            LAST_URL=$(tail -1 "$URL_LOG")
            log_message "Will resume from: $LAST_URL"
            log_message "Keep URL log for resume"
        else
            log_message "No URL log found - may need to retry from start"
        fi
    fi
    
    # Kill Claude
    kill_claude
    
    # Move URL log to permanent storage if successful
    if [ $SUCCESS -eq 1 ] && [ -f "$URL_LOG" ]; then
        PERM_URL_LOG="$URL_LOG_DIR/uni_$(printf '%03d' $NEXT_START)_urls.txt"
        log_message "Moving URL log to permanent storage: $PERM_URL_LOG"
        mv "$URL_LOG" "$PERM_URL_LOG"
    elif [ $SUCCESS -eq 1 ]; then
        # Even if no URL log in tmp (fresh run), create one for the record
        PERM_URL_LOG="$URL_LOG_DIR/uni_$(printf '%03d' $NEXT_START)_urls.txt"
        echo "No URL tracking from this run - completed in single session" > "$PERM_URL_LOG"
    fi
    
    log_message "Waiting 2 seconds before next batch..."
    sleep 2
done

log_message ""
log_message "=================================================="
log_message "SCRAPING COMPLETE!"
log_message "Batch files in: $BATCH_DIR"
log_message "Check logs in: $LOG_DIR"