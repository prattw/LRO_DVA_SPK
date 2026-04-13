# vantage-preprocess

Document preprocessing pipeline for Army Vantage–style ingestion: **PDF, DOCX, TXT, CSV, Excel (xlsx),** and scanned images → structured **JSONL**, **CSV**, **XLSX**, and **plain `.txt` chunks** (for the Army Vantage web uploader) exports.

## Requirements

- **Python 3.11+** (test on 3.11 for Windows deployments)
- **Tesseract** on `PATH` for OCR (recommended for scans)

## Army Vantage: OCR on the Mac, then upload portal `.txt`

Vantage Code Workspace does not provide Tesseract. Run preprocessing **on a machine you control** (e.g. Mac Mini), then upload **plain text** into Agent Studio — not raw JSON/CSV as “documents” (see `docs/API_ARMY_VANTAGE.md`).

1. **Install Tesseract** (once): `brew install tesseract`
2. **Install the project** (see [Install](#install))
3. **Check the machine**: `./scripts/check_mac_prereqs.sh`
4. **Run the pipeline** (writes JSONL/CSV + `vantage_portal_txt/*.txt`):

   ```bash
   ./scripts/run_portal_txt_for_vantage.sh /path/to/specs_or_folder ./out_upload
   ```

5. **Upload** the files under `out_upload/vantage_portal_txt/` in Agent Studio’s document dialog.  
6. **Keep** `out_upload/vantage_master.jsonl` (and `.csv`) for downstream warehouse / ontology work — same run, fixed columns, no re-OCR later.

**Repo in iCloud Drive:** Python may skip hidden `.pth` files in `.venv`; the scripts set `PYTHONPATH` to `./src` so `vantage-preprocess` always imports. For manual runs: `export PYTHONPATH="$PWD/src"`.

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
export PYTHONPATH=./src   # recommended if the repo lives in iCloud Drive
vantage-preprocess ./path/to/files --out ./out --formats jsonl,csv,txt
# or: ./scripts/run_portal_txt_for_vantage.sh ./path/to/files ./out
```

## API (optional)

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Unix

vantage-api
# or: python -m vantage_api
```

- **Swagger:** `http://127.0.0.1:8000/docs`
- **Browser UI:** `http://127.0.0.1:8000/ui/`
- **Health:** `GET /health`

Upload → job status → ZIP download are on `POST /upload-and-process`, `GET /status/{job_id}`, `GET /download/{job_id}` (see `docs/API_ARMY_VANTAGE.md`).

### Docker (local or cloud)

```bash
docker build -t vantage-api .
docker run --rm -p 8000:8000 -v vantage-data:/data vantage-api
```

Deploy options: `docs/ONLINE.md` (Render blueprint `render.yaml`, tunnels, Fly).

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
