#!/usr/bin/env bash
# Verify Mac Mini / laptop is ready for OCR + Army Vantage portal .txt export.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
ERR=0

echo "== Python venv =="
if [[ ! -x .venv/bin/python ]]; then
  echo "  Missing .venv — run: ./scripts/recreate_venv.sh"
  ERR=1
else
  echo "  OK: $(.venv/bin/python --version)"
fi

echo "== Tesseract (required for scanned PDFs) =="
if ! command -v tesseract &>/dev/null; then
  echo "  Not found. Install: brew install tesseract"
  ERR=1
else
  echo "  OK: $(command -v tesseract)"
  tesseract --version 2>&1 | head -1
fi

echo "== pytesseract sees Tesseract =="
if [[ -x .venv/bin/python ]]; then
  if .venv/bin/python -c "import pytesseract; pytesseract.get_tesseract_version(); print('  OK')" 2>/dev/null; then
    :
  else
    echo "  Failed — is Tesseract on PATH when Python runs?"
    ERR=1
  fi
fi

if [[ "$ERR" -ne 0 ]]; then
  echo ""
  echo "Fix the items above, then run: ./scripts/run_portal_txt_for_vantage.sh <input> <out_dir>"
  exit 1
fi
echo ""
echo "All checks passed."
