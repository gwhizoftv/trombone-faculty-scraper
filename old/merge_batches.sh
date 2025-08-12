#!/bin/bash
# Merge all batch CSV files into final result

echo "Merging batch CSV files..."

OUTPUT="results/trombone_faculty_final.csv"

# Write header once
echo "University,Faculty Name,Title,Email,Phone,Profile URL,Notes" > "$OUTPUT"

# Append all batch files (skip headers)
for batch in results/batches/batch_*.csv; do
    if [ -f "$batch" ]; then
        echo "Adding: $batch"
        tail -n +2 "$batch" >> "$OUTPUT"
    fi
done

# Count results
TOTAL=$(tail -n +2 "$OUTPUT" | wc -l | tr -d ' ')
echo ""
echo "Merge complete!"
echo "Total faculty records: $TOTAL"
echo "Output file: $OUTPUT"

# Also show universities with no trombone faculty
if [ -f "results/no_trombone_found.csv" ]; then
    NO_TROMBONE=$(tail -n +2 results/no_trombone_found.csv | wc -l | tr -d ' ')
    echo "Universities with no trombone faculty: $NO_TROMBONE"
fi