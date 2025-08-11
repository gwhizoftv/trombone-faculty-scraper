#!/bin/bash
# View URL logs for completed universities

URL_LOG_DIR="results/url_logs"

if [ ! -d "$URL_LOG_DIR" ]; then
    echo "No URL logs directory found yet."
    exit 1
fi

echo "URL Logs for Completed Universities"
echo "===================================="

for log in "$URL_LOG_DIR"/uni_*.txt; do
    if [ -f "$log" ]; then
        UNI_NUM=$(basename "$log" | sed 's/uni_//;s/_urls.txt//')
        echo ""
        echo "University #$UNI_NUM:"
        echo "---------------"
        cat "$log"
    fi
done

echo ""
echo "===================================="
echo "Total URL log files: $(ls -1 "$URL_LOG_DIR"/uni_*.txt 2>/dev/null | wc -l | tr -d ' ')"