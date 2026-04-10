# vantage-preprocess

Document preprocessing pipeline for Army Vantage–style ingestion: **PDF, DOCX, TXT, CSV, Excel (xlsx),** and scanned images → structured **JSONL**, **CSV**, and **XLSX** exports.

## Requirements

- **Python 3.11+** (test on 3.11 for Windows deployments)
- **Tesseract** on `PATH` for OCR (recommended for scans)

## Project layout

```text
army-vantage-preprocess/
├── config/                 # Example YAML (sample; not loaded by CLI yet)
│   └── vantage.example.yaml
├── src/
│   ├── vantage_preprocess/ # Core library + CLI (pipeline, extract, export)
│   └── vantage_api/        # Optional FastAPI app (`[api]` extra)
├── tests/
├── pyproject.toml
├── requirements.txt        # Points to editable install; deps live in pyproject.toml
├── .env.example            # API / future services (copy to `.env`)
└── README.md
```

**Core** (`vantage_preprocess`): intake, extraction, OCR fallback, sectioning, chunking, export—**no FastAPI dependency**.

**Web** (`vantage_api`): HTTP layer only; depends on the core package. Install with `pip install -e ".[api]"`.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -U pip
pip install -e ".[dev]"
# Optional API:
pip install -e ".[dev,api]"
```

## CLI

```bash
python -m vantage_preprocess run ./path/to/files --out ./out --formats jsonl,csv,xlsx
```

## API (optional)

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Unix

vantage-api
# or: python -m vantage_api
```

Open `http://127.0.0.1:8000/docs` for OpenAPI. `/health` is wired; upload/job routes come later.

## Configuration

- **Example pipeline YAML:** `config/vantage.example.yaml` (for future `--config` wiring).
- **API / env:** `.env.example` → `.env` (see `vantage_api/settings.py`).

## Development

```bash
ruff check src tests
ruff format src tests
pytest
```

## License

Use per your organization’s policy.
