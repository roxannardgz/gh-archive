#!/bin/bash

if date -u -v-1d +"%Y-%m-%d" >/dev/null 2>&1; then
  # macOS
  YESTERDAY=$(date -u -v-1d +"%Y-%m-%d")
else
  # Linux
  YESTERDAY=$(date -u -d "yesterday" +"%Y-%m-%d")
fi

bruin run \
  --start-date "${1:-${YESTERDAY}T00:00:00Z}" \
  --end-date "${2:-${YESTERDAY}T23:59:59Z}" \
  pipeline/cloud/assets/*.py \
  pipeline/cloud/assets/*.sql