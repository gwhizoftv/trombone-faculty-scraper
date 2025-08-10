#!/bin/bash
# Monitor Claude Desktop's status

while true; do
    clear
    echo "=== CLAUDE DESKTOP MONITOR ==="
    echo "Time: $(date)"
    echo ""
    
    if [ -f claude_status.txt ]; then
        cat claude_status.txt
    else
        echo "No status file found"
    fi
    
    echo ""
    echo "---"
    
    # Check progress
    if [ -f progress_tracker.txt ]; then
        echo "Progress:"
        cat progress_tracker.txt
    fi
    
    echo ""
    echo "---"
    
    # Check latest batch file
    LATEST_BATCH=$(ls -t batches/batch_*.csv 2>/dev/null | head -1)
    if [ -n "$LATEST_BATCH" ]; then
        echo "Latest batch: $LATEST_BATCH"
        echo "Lines: $(wc -l < "$LATEST_BATCH")"
    fi
    
    echo ""
    echo "Press Ctrl+C to stop monitoring"
    sleep 5
done