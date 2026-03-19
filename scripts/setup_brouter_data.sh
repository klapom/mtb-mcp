#!/bin/bash
# Download BRouter segment data for Germany
# Run this once before using BRouter routing

set -euo pipefail

SEGMENTS_DIR="data/brouter/segments4"
BASE_URL="https://brouter.de/brouter/segments4"

echo "=== BRouter Segment Data Setup ==="
echo "Downloading segment data for Germany..."

mkdir -p "$SEGMENTS_DIR"

# Germany coverage: roughly E5-E16, N47-N55
for lon in $(seq 5 15); do
    for lat in $(seq 47 54); do
        file="E${lon}_N${lat}.rd5"
        if [ ! -f "$SEGMENTS_DIR/$file" ]; then
            echo "Downloading $file..."
            curl -sS -o "$SEGMENTS_DIR/$file" "$BASE_URL/$file" || echo "  (not available)"
        else
            echo "  $file already exists, skipping"
        fi
    done
done

echo ""
echo "Done! Segment data in: $SEGMENTS_DIR"
echo "Total size: $(du -sh "$SEGMENTS_DIR" | cut -f1)"
