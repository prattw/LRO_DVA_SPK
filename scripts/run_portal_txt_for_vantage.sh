#!/usr/bin/env bash
# Run preprocessing on your Mac (with Tesseract) and write JSONL/CSV + Army Vantage portal .txt chunks.
# Usage:
#   ./scripts/run_portal_txt_for_vantage.sh /path/to/specs.pdf ./out_run
#   ./scripts/run_portal_txt_for_vantage.sh /path/to/folder ./out_run
#
# Upload files from: <out_dir>/vantage_portal_txt/*.txt into Agent Studio (not JSON/CSV as documents).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Editable installs rely on .pth files; on iCloud Drive those files are often marked
# "hidden" and Python 3.11 skips them — force src on the path.
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <input_file_or_directory> <output_directory>" >&2
  exit 1
fi
INPUT="$1"
OUT="$2"

if [[ ! -e "$INPUT" ]]; then
  echo "Not found: $INPUT" >&2
  exit 1
fi

"$ROOT/scripts/check_mac_prereqs.sh"

mkdir -p "$OUT"
VENV_RUN="${ROOT}/.venv/bin/vantage-preprocess"
if [[ ! -x "$VENV_RUN" ]]; then
  echo "Install the package: pip install -e ." >&2
  exit 1
fi

echo "Running pipeline → $OUT"
"$VENV_RUN" "$INPUT" --out "$OUT" --formats jsonl,csv,txt

PORTAL="${OUT}/vantage_portal_txt"
echo ""
echo "Done."
echo "  Manifest / full ingestion (JSONL/CSV): $OUT"
echo "  Workshop master (slim columns for ontology / warehouse): $OUT/vantage_master.jsonl and .csv"
echo "  Upload these plain-text chunks to Army Vantage: $PORTAL"
if [[ -d "$PORTAL" ]]; then
  n=$(find "$PORTAL" -name '*.txt' 2>/dev/null | wc -l | tr -d ' ')
  echo "  ($n .txt file(s))"
fi
