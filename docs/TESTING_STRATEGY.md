# Testing strategy — FastAPI preprocessing system

This document describes how to test the **Army Vantage** stack: FastAPI job API (`vantage_api`), batch orchestration (`run_batch` / `execute_upload_job`), **extraction** (PDF/DOCX/TXT, OCR paths), **chunking** (word limits, overlap), **exports** (CSV / JSONL / XLSX), and **error handling**.

## Goals

| Goal | What to assert |
|------|----------------|
| Correctness | Outputs match contracts (schemas, column sets, chunk bounds). |
| Regression | Changes to extract/chunk/export do not break known-good fixtures. |
| Resilience | Bad inputs fail at the right **stage** (`intake` vs `extract`) with clear messages. |
| API behavior | HTTP status codes, async job flow (`202` → poll → `complete` / `failed`), download `409` / `404`. |

## Test pyramid

```
        ┌─────────────┐
        │  E2E / API  │  few: full upload → ZIP (optional, slower)
        └──────┬──────┘
     ┌─────────┴─────────┐
     │  Integration      │  pipeline + FastAPI TestClient + tmp dirs
     └─────────┬─────────┘
  ┌────────────┴────────────┐
  │  Unit                   │  pure functions, config, validators, scoring
  └─────────────────────────┘
```

- **Unit** (fast, no I/O): `ChunkingConfig` validation, `validate_chunks`, `summarize_job_quality`, merge/split helpers, ID formatting.
- **Integration** (disk + same process): `run_batch` on temp files, `TestClient` against `create_app()` with `VANTAGE_DATA_DIR` under `tmp_path`.
- **E2E** (optional / CI nightly): real scanned PDFs, large files, full ZIP inspection — mark `@pytest.mark.slow` or run in a separate job.

## Layout (pytest)

| Path | Purpose |
|------|---------|
| `tests/conftest.py` | Shared fixtures (extend with sample assets). |
| `tests/integration/` | API + pipeline cross-module tests; uses `TestClient`, `tmp_path`. |
| `tests/test_*.py` | Focused unit tests (chunk, extract, export, domain). |

Suggested **markers** (registered in `pyproject.toml`):

- `integration` — uses `TestClient`, temp files, or multi-stage pipeline.
- `api` — requires `fastapi` / `multipart` (use `pytest.importorskip`).
- `ocr` — needs Tesseract / heavy deps; skip in minimal CI if needed.
- `slow` — large PDFs or many iterations.

Run subsets:

```bash
pytest tests/ -m "not slow"
pytest tests/integration/ -v
```

## What to test by subsystem

### 1. File upload endpoint (`POST /upload-and-process`)

- **202** + JSON body: `job_id`, `status`, `status_url`.
- **400** empty multipart (`files` missing).
- **400** disallowed extension (e.g. `.exe`).
- **413** when file exceeds `VANTAGE_MAX_UPLOAD_BYTES` (set env small in test).

**Tooling:** `httpx` / Starlette `TestClient`, `io.BytesIO` for in-memory “files”:

```python
client.post("/upload-and-process", files=[("files", ("a.txt", io.BytesIO(b"..."), "text/plain"))])
```

### 2. Batch processing (`run_batch`, `execute_upload_job`)

- Multiple paths → `per_file` length equals input count.
- One file fails → others still processed; `errors` list and `failure_count` consistent.
- **Progress hook** (`on_file_done`): indices and cumulative chunk counts monotonic.

### 3. Extraction pipeline

- **TXT / DOCX / PDF** (native text): structured document has expected `pages`, `overall_extract_method`.
- **OCR fallback** (scanned PDF): assert `ExtractMethod.OCR` or `HYBRID` when native text is sparse — often easier to **mock** `extract_pdf_document` / engine to return a controlled `StructuredDocument` so CI does not require Tesseract + fixtures.
- **Corrupted PDF**: expect `extract` stage failure (e.g. PyMuPDF `FileDataError` surfaced as message).
- **Empty file**: intake succeeds; pipeline may yield **0 chunks** and `success=True` (current behavior for empty `.txt`).

### 4. OCR fallback

- **Unit-style:** `unittest.mock.patch` on `vantage_preprocess.extract.engine.extract_pdf_document` (or `analyze_native_pages`) to force OCR path and assert `PageText.method` / `confidence`.
- **Optional integration:** minimal scanned PDF in `tests/fixtures/` + `@pytest.mark.ocr` if CI has Tesseract.

### 5. Chunking rules

- **Hard cap:** every `ExportRow.chunk_word_count <= ChunkingConfig.max_words` (after overlap).
- **Validation:** `validate_chunks` records **errors** if any segment exceeds `max_words` (should not happen after engine).
- **Overlap:** with two segments, later chunk text includes tail of previous when configured.

Use tight `ChunkingConfig` in tests (e.g. `max_words=80`, `min_words=20`) for fast feedback.

### 6. Export correctness

- `VantageIngestionRecord.from_export_row` → CSV/JSONL columns match `BaseVantageExporter.columns`.
- Round-trip: write CSV with `write_csv`, parse header + one row.
- Quality fields present when scoring ran (`chunk_quality_score`, etc.).

### 7. Error handling

- Pipeline: intake error vs extract error → correct `failure_stage` on `PerFileOutcome`.
- API: unknown `job_id` → **404**; download while running → **409**.

### 8. Status polling (`GET /status/{job_id}`)

- While job `processing`: `progress.files_processed` / `files_total`, `chunks_created` update.
- On `complete`: `summary`, `quality_summary` (if present), `download_path`.
- On `failed`: `message` set.

Poll in tests with a small loop + timeout (see `tests/test_api_jobs.py`).

## Edge cases (checklist)

| Case | Expectation |
|------|-------------|
| Empty `.txt` | No chunks or empty export; document still “success” if no exception. |
| Corrupted `.pdf` | Extract fails; `failure_stage == "extract"`. |
| Scanned PDF | OCR path; optional mock or `@pytest.mark.ocr` integration. |
| Huge single paragraph | Chunks split; none over `max_words`. |
| Concurrent jobs | Separate `job_id` dirs under `VANTAGE_DATA_DIR` (store is in-memory — restart clears). |

## CI recommendations

1. **Default job:** `pytest -q`, Python 3.11+, install `.[dev,api]`.
2. **Coverage:** `pytest --cov=vantage_preprocess --cov=vantage_api` (threshold optional).
3. **Lint:** `ruff check src tests`.
4. **Artifacts:** upload HTML coverage on failure only.

## References (in-repo)

- API jobs: `tests/test_api_jobs.py`, `tests/test_api_health.py`, `tests/test_ui_static.py`
- **Integration (examples):** `tests/integration/test_api_upload_and_poll.py`, `tests/integration/test_pipeline_file_edges.py`, `tests/integration/test_chunk_and_export_limits.py`, `tests/integration/test_extraction_ocr_mock.py`
- Batch: `tests/test_batch_per_file.py`
- Chunking: `tests/test_chunk.py`
- Export: `tests/test_export_ingestion.py`
- Quality: `tests/test_quality_scoring.py`
- Shared API fixture: `tests/integration/conftest.py`
