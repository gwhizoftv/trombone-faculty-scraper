#!/bin/bash
# Reset incomplete university marker if needed

echo "Checking for incomplete university processing..."

if [ -f "tmp/incomplete_university.json" ]; then
    echo "Found incomplete marker:"
    cat tmp/incomplete_university.json
    echo ""
    read -p "Do you want to remove this and start fresh? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm tmp/incomplete_university.json
        echo "Incomplete marker removed."
        
        # Also check for URL log
        if ls tmp/uni_*_urls.txt 1> /dev/null 2>&1; then
            echo "Found URL logs:"
            ls -la tmp/uni_*_urls.txt
            read -p "Remove URL logs too? (y/n): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm tmp/uni_*_urls.txt
                echo "URL logs removed."
            fi
        fi
    else
        echo "Keeping incomplete marker - will resume on next run."
    fi
else
    echo "No incomplete university found - system is ready."
fi