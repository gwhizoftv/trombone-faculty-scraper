#!/bin/bash
# Smart Email Finder - Second pass focusing on missing emails

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
LOG_FILE="$LOG_DIR/email_finder_${TIMESTAMP}.log"

# Function to log to both file and terminal
log_message() {
    echo "$1" | tee -a "$LOG_FILE"
}

log_message "Starting EMAIL FINDER - Second Pass"
log_message "Log file: $LOG_FILE"
log_message "=================================================="

# Configuration
MAX_WAIT_MINUTES=5   # More time for deeper searching

# Initialize email finder progress tracker
if [ ! -f email_finder_progress.txt ]; then
    echo "LAST_PROCESSED=0" > email_finder_progress.txt
    # Count lines in universities_missing_emails.csv minus header
    TOTAL=$(tail -n +2 universities_missing_emails.csv | wc -l | tr -d ' ')
    echo "TOTAL_UNIVERSITIES=$TOTAL" >> email_finder_progress.txt
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
    LAST=$(grep LAST_PROCESSED email_finder_progress.txt | cut -d'=' -f2 | tr -d ' ')
    TOTAL=$(grep TOTAL_UNIVERSITIES email_finder_progress.txt | cut -d'=' -f2 | tr -d ' ')
    
    if [ "$LAST" -ge "$TOTAL" ]; then
        log_message "All universities processed for missing emails!"
        break
    fi
    
    log_message ""
    log_message "=========================================="
    log_message "Email Finder Progress: $LAST / $TOTAL universities"
    log_message "=========================================="
    
    # Kill Claude if running
    if pgrep -x "Claude" > /dev/null; then
        log_message "Claude still running, stopping..."
        kill_claude
    fi
    
    # Determine which university to process
    NEXT_START=$((LAST + 1))
    BATCH_FILE="results/batches/email_pass2_$(printf '%03d' $NEXT_START).csv"
    URL_LOG="tmp/email_pass2_$(printf '%03d' $NEXT_START)_urls.txt"
    
    log_message "Will create: $BATCH_FILE"
    
    # Generate prompt for finding missing emails
    python3 generate_email_finder_prompt.py
    
    # Save prompt to logs
    cp current_prompt.txt "$LOG_DIR/email_prompt_${NEXT_START}.txt"
    
    log_message "Processing university #$NEXT_START for missing emails..."
    
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
    screencapture -x "debug_screenshots/email_finder_$(date +%Y%m%d_%H%M%S).png"
    
    log_message "Claude is searching for emails..."
    
    # Monitor for completion - give more time for deep searching
    SECONDS_WAITED=0
    MAX_SECONDS=$((MAX_WAIT_MINUTES * 60))
    SUCCESS=0
    
    while [ $SECONDS_WAITED -lt $MAX_SECONDS ]; do
        # Check progress update
        CURRENT_PROGRESS=$(grep LAST_PROCESSED email_finder_progress.txt | cut -d'=' -f2 | tr -d ' ')
        
        if [ "$CURRENT_PROGRESS" -gt "$LAST" ]; then
            log_message "SUCCESS: Progress updated to $CURRENT_PROGRESS"
            SUCCESS=1
            break
        fi
        
        # Check if batch file exists
        if [ -f "$BATCH_FILE" ]; then
            LINES=$(wc -l < "$BATCH_FILE" | tr -d ' ')
            if [ $LINES -gt 0 ]; then
                log_message "Batch file created with $LINES lines"
                SUCCESS=1
                # Update progress
                sed -i '' "s/LAST_PROCESSED=.*/LAST_PROCESSED=$NEXT_START/" email_finder_progress.txt
                break
            fi
        fi
        
        # Progress indicator every 20 seconds
        if [ $((SECONDS_WAITED % 20)) -eq 0 ] && [ $SECONDS_WAITED -gt 0 ]; then
            log_message "  Searching... (${SECONDS_WAITED}s elapsed)"
        fi
        
        sleep 1
        SECONDS_WAITED=$((SECONDS_WAITED + 1))
    done
    
    if [ $SECONDS_WAITED -ge $MAX_SECONDS ]; then
        log_message "TIMEOUT after $MAX_WAIT_MINUTES minutes - may need manual search"
    fi
    
    # Kill Claude
    kill_claude
    
    # Move URL log if exists
    if [ -f "$URL_LOG" ]; then
        PERM_URL_LOG="$URL_LOG_DIR/email_pass2_$(printf '%03d' $NEXT_START)_urls.txt"
        mv "$URL_LOG" "$PERM_URL_LOG"
        log_message "URL log moved to: $PERM_URL_LOG"
    fi
    
    log_message "Waiting 2 seconds before next university..."
    sleep 2
done

log_message ""
log_message "=================================================="
log_message "EMAIL FINDING COMPLETE!"
log_message "Results in: $BATCH_DIR"
log_message "Check logs in: $LOG_DIR"