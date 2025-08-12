#!/bin/bash
# Smart automated scraping V2 - with better resume logic

# Setup logging
LOG_DIR="logs"
BATCH_DIR="results/batches"
TMP_DIR="tmp"
URL_LOG_DIR="results/url_logs"
# Directories should already exist from setup_instrument_search.sh
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/scraper_${TIMESTAMP}.log"

# Function to log to both file and terminal
log_message() {
    echo "$1" | tee -a "$LOG_FILE"
}

log_message "Starting SMART AUTOMATED trombone faculty scraping V2"
log_message "Log file: $LOG_FILE"
log_message "=================================================="

# Configuration
MAX_WAIT_MINUTES=3   # 3 minutes for one university

# Progress tracker should already exist from setup_instrument_search.sh
if [ ! -f progress_tracker.txt ]; then
    log_message "ERROR: progress_tracker.txt not found. Run setup script first."
    exit 1
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
    # Fix corrupted progress_tracker.txt if needed
    if ! grep -q "^TOTAL_UNIVERSITIES=" progress_tracker.txt; then
        log_message "WARNING: progress_tracker.txt appears corrupted, attempting to fix..."
        LAST_VAL=$(grep -o "LAST_PROCESSED=[0-9]*" progress_tracker.txt | cut -d'=' -f2)
        if [ -n "$LAST_VAL" ]; then
            echo "LAST_PROCESSED=$LAST_VAL" > progress_tracker.txt
            echo "TOTAL_UNIVERSITIES=202" >> progress_tracker.txt
            log_message "Fixed progress_tracker.txt with LAST_PROCESSED=$LAST_VAL"
        else
            log_message "ERROR: Could not recover progress, resetting to 0"
            echo "LAST_PROCESSED=0" > progress_tracker.txt
            echo "TOTAL_UNIVERSITIES=202" >> progress_tracker.txt
        fi
    fi
    
    # Read current progress
    LAST=$(grep "^LAST_PROCESSED=" progress_tracker.txt | cut -d'=' -f2 | tr -d ' ')
    TOTAL=$(grep "^TOTAL_UNIVERSITIES=" progress_tracker.txt | cut -d'=' -f2 | tr -d ' ')
    
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
    
    # Update Claude Desktop config to set working directory
    CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    CURRENT_DIR=$(pwd)
    
    if [ -f "$CONFIG_FILE" ]; then
        # Backup original config
        cp "$CONFIG_FILE" "$CONFIG_FILE.bak"
        
        # Update the cwd in the config using Python (more reliable for JSON)
        python3 -c "
import json
import sys

config_file = '$CONFIG_FILE'
current_dir = '$CURRENT_DIR'

try:
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Update global cwd setting
    config['cwd'] = current_dir
    
    # Also update MCP server settings to use current directory
    if 'mcpServers' in config:
        for server_name, server_config in config['mcpServers'].items():
            # Update cwd for each server
            server_config['cwd'] = current_dir
            
            # For filesystem server, update the allowed path argument
            if server_name == 'filesystem' and 'args' in server_config:
                # Replace the last argument (the allowed path) with current directory
                if len(server_config['args']) > 0:
                    server_config['args'][-1] = current_dir
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f'Updated Claude Desktop config: cwd = {current_dir}')
    print(f'Updated all MCP servers to use: {current_dir}')
except Exception as e:
    print(f'Error updating config: {e}')
    sys.exit(1)
"
        
        if [ $? -eq 0 ]; then
            log_message "Updated Claude Desktop working directory to: $CURRENT_DIR"
            log_message "Updated all MCP servers to use: $CURRENT_DIR"
            log_message "IMPORTANT: Claude Desktop needs to be fully restarted to reload config"
            
            # Kill Claude to force restart with new config
            kill_claude
            sleep 2
        else
            log_message "Warning: Could not update Claude Desktop config"
        fi
    else
        log_message "Warning: Claude Desktop config not found at $CONFIG_FILE"
    fi
    
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
        CURRENT_PROGRESS=$(grep "^LAST_PROCESSED=" progress_tracker.txt | cut -d'=' -f2 | tr -d ' ')
        
        # Validate that CURRENT_PROGRESS is a number
        if [[ "$CURRENT_PROGRESS" =~ ^[0-9]+$ ]] && [ "$CURRENT_PROGRESS" -gt "$LAST" ]; then
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