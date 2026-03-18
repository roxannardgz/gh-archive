#!/usr/bin/env bash

set -euo pipefail

RAW_DIR="data/raw"
EXPECTED_FILES=24
MIN_BYTES=1000000

actual_files=$(find "$RAW_DIR" -maxdepth 1 -name '*.json.gz' | wc -l | tr -d ' ')

if [ "$actual_files" -ne "$EXPECTED_FILES" ]; then
  echo "Expected $EXPECTED_FILES files, found $actual_files"
  exit 1
fi

for file in "$RAW_DIR"/*.json.gz; do
  echo "Validating $file"

  gunzip -t "$file"

  size=$(stat -f%z "$file")
  if [ "$size" -lt "$MIN_BYTES" ]; then
    echo "File is too small: $file ($size bytes)"
    exit 1
  fi
done

echo "All files passed validation."