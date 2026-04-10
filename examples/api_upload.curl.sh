#!/usr/bin/env bash
# Example: upload two text files and receive JSON summary + download URL.
# Requires: pip install 'vantage-preprocess[api]' and running the server:
#   vantage-api
# or:
#   python -m vantage_api

set -euo pipefail
BASE="${VANTAGE_API_BASE:-http://127.0.0.1:8000}"

echo "== JSON response (default) =="
curl -sS -X POST "${BASE}/upload-and-process" \
  -F "files=@${1:-README.md}" \
  -F "files=@${2:-README.md}" \
  | python -m json.tool

echo ""
echo "== Direct ZIP download =="
curl -sS -OJ -X POST "${BASE}/upload-and-process?delivery=zip" \
  -F "files=@${1:-README.md}"

echo "Saved ZIP in current directory."
