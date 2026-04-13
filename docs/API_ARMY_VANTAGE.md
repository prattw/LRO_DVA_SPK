# Army Vantage FastAPI backend

Modular layout:

| Layer | Role |
|-------|------|
| `vantage_api.routes.*` | HTTP validation, job registration, background enqueue |
| `vantage_api.jobs.executor` | Blocking pipeline + job store updates (reusable from a future worker) |
| `vantage_api.processing.runner` | ZIP packaging, `processing_report.json` |
| `vantage_preprocess.services.pipeline` | Extraction → chunking → CSV/JSONL/XLSX + portal ``.txt`` |

Processing is **fully automatic** after upload (no extra user input). The API returns a **`job_id` immediately** (`202 Accepted`); work runs in a **background thread** so the client should **poll** `GET /status/{job_id}` until `status` is `complete` or `failed`, then call `GET /download/{job_id}`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload-and-process` | Multipart upload; enqueue extraction → chunking → export; **returns at once** with `job_id`. |
| `GET` | `/status/{job_id}` | `status`, **progress**, **chunk count**, **errors**, optional **`quality_summary`**, optional `summary` when done. |
| `GET` | `/download/{job_id}` | ZIP when `status` is `complete` (`409` if still running or failed without a bundle). Includes `output/vantage_portal_txt/*.txt` for **vantage.army.mil** Agent Studio (plain text uploads). |
| `GET` | `/health` | Liveness. |

### Query parameters (`POST /upload-and-process`)

- `include_xlsx` (bool, default **`true`**): include `vantage_chunks.xlsx` in the ZIP.

### Army Vantage web upload (Agent Studio)

The hosted uploader accepts **PDFs, Office documents, presentations, and text files**; it does **not** treat CSV/JSONL/JSON as documents. Each job therefore includes **`output/vantage_portal_txt/`** — one UTF-8 **`.txt` per chunk** (with short `#` comment headers for `chunk_id`, source, pages). Oversized chunks are split so each file stays under **`VANTAGE_PORTAL_TXT_MAX_BYTES`** (default 9 MiB). Upload those `.txt` files (or zip subsets) into Agent Studio’s **Upload documents** dialog.

## Example: POST response (`202 Accepted`)

```http
HTTP/1.1 202 Accepted
Content-Type: application/json
```

```json
{
  "job_id": "01bff3e784e741698ff58909f53c5e6b",
  "status": "processing",
  "message": "Processing started. Poll GET /status/01bff3e784e741698ff58909f53c5e6b until complete.",
  "status_url": "/status/01bff3e784e741698ff58909f53c5e6b"
}
```

## Example: GET status while running

```json
{
  "job_id": "01bff3e784e741698ff58909f53c5e6b",
  "status": "processing",
  "progress": {
    "files_processed": 0,
    "files_total": 2,
    "chunks_created": 0
  },
  "chunks_created": 0,
  "errors": [],
  "created_at": "2026-04-10T18:00:00+00:00",
  "finished_at": null,
  "summary": null,
  "quality_summary": null,
  "download_path": null,
  "message": null
}
```

## Example: GET status when complete

```json
{
  "job_id": "01bff3e784e741698ff58909f53c5e6b",
  "status": "complete",
  "progress": {
    "files_processed": 2,
    "files_total": 2,
    "chunks_created": 14
  },
  "chunks_created": 14,
  "errors": [],
  "created_at": "2026-04-10T18:00:00+00:00",
  "finished_at": "2026-04-10T18:00:05+00:00",
  "summary": {
    "files_submitted": 2,
    "files_processed_ok": 2,
    "failures": 0,
    "chunks_created": 14,
    "errors": [],
    "per_file": [],
    "warnings": []
  },
  "quality_summary": {
    "chunks_total": 14,
    "low_quality_chunks": 0,
    "documents_needing_review": 0,
    "mean_chunk_quality_score": 0.8521,
    "fraction_low_quality": 0.0
  },
  "download_path": "/download/01bff3e784e741698ff58909f53c5e6b",
  "message": null
}
```

`status` values: `pending` | `processing` | **`complete`** | `failed`.

## Example `curl`

**1. Upload (get `job_id` immediately)**

```bash
export BASE=http://127.0.0.1:8000
curl -sS -D - -X POST "$BASE/upload-and-process" \
  -F "files=@./spec.pdf" \
  -F "files=@./notes.txt"
```

**2. Poll status**

```bash
JOB_ID='<paste job_id from JSON>'
curl -sS "$BASE/status/$JOB_ID" | jq .
```

**3. Download ZIP**

```bash
curl -sS -OJ "$BASE/download/$JOB_ID"
```

**Optional:** omit Excel from the bundle:

```bash
curl -sS -X POST "$BASE/upload-and-process?include_xlsx=false" \
  -F "files=@./notes.txt"
```

## Frontend (`fetch`) sketch

```javascript
const fd = new FormData();
files.forEach((f) => fd.append("files", f));

const up = await fetch("/upload-and-process", { method: "POST", body: fd });
if (up.status !== 202) throw new Error(await up.text());
const { job_id, status_url } = await up.json();

let st;
do {
  await new Promise((r) => setTimeout(r, 500));
  st = await (await fetch(status_url)).json();
} while (st.status === "processing" || st.status === "pending");

if (st.status !== "complete") throw new Error(st.message || "job failed");

const blob = await (await fetch(`/download/${job_id}`)).blob();
```

## ZIP contents

- `output/vantage_chunks.jsonl` — combined NDJSON (full ingestion columns)  
- `output/vantage_chunks.csv` — combined UTF-8 CSV  
- `output/vantage_master.jsonl` — slim NDJSON for Workshop / ontology (`source_file`, `source_spec`, `section_number`, `section_title`, `chunk_id`, `chunk_text`, `page_start`, `page_end`, `extraction_method`)  
- `output/vantage_master.csv` — same schema as UTF-8 CSV  
- `output/vantage_chunks.xlsx` — when `include_xlsx=true` (default)  
- `output/run_manifest.json` — batch manifest (includes `quality_summary` when enabled; `workshop_master` paths when rows exist)  
- `output/per_file_results.json` — per input file  
- `output/errors_report.json` — structured failures  
- `processing_report.json` — job-level summary (`quality_summary`, …)  
- `job_metadata.json` — pipeline snapshot  

Failures on one file do not stop other files in the same upload.

## Future: async workers

Swap `BackgroundTasks` + `run_in_threadpool` for Celery/RQ: call `execute_upload_job(...)` from the worker with the same arguments; keep routes thin.

## Configuration

See `.env.example`: `VANTAGE_DATA_DIR`, `VANTAGE_MAX_UPLOAD_BYTES`, `VANTAGE_MAX_FILES_PER_JOB`, optional `VANTAGE_CHUNK_*` overrides.

## Run the API

```bash
uvicorn vantage_api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Open `/docs` for interactive OpenAPI (Swagger UI).
