#!/usr/bin/env bash
# Recreate .venv using the newest Python you choose.
# After installing Python from python.org, use e.g.:
#   ./scripts/recreate_venv.sh /Library/Frameworks/Python.framework/Versions/3.14/bin/python3
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Prefer 3.14+ when installed (e.g. /usr/local/bin/python3.14); override with first arg.
PY="${1:-$(command -v python3.14 2>/dev/null || command -v python3 || echo python3)}"
cd "$ROOT"
if [[ -d .venv ]]; then
  echo "Removing existing .venv"
  rm -rf .venv
fi
echo "Creating venv with: $PY"
"$PY" -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
python -m pytest tests/ -q
echo "OK: $(python --version) at $(command -v python)"
