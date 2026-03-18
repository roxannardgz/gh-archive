#!/usr/bin/env bash

set -euo pipefail

BASE_URL="https://data.gharchive.org"
OUTPUT_DIR="data/raw"

mkdir -p "$OUTPUT_DIR"

for hour in {0..23}; do
  file="2025-03-15-${hour}.json.gz"
  url="${BASE_URL}/${file}"

  if [ -f "${OUTPUT_DIR}/${file}" ]; then
    echo "Skipping ${file} (already exists)"
  else
    echo "Downloading ${file}"
    curl -f -L -o "${OUTPUT_DIR}/${file}" "$url"
  fi
done