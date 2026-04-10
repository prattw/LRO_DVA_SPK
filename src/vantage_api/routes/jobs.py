"""
Upload and processing endpoints.

The HTTP layer validates uploads, persists bytes under ``VANTAGE_DATA_DIR/jobs/{job_id}/``,
registers a :class:`~vantage_api.jobs.store.JobRecord`, and returns **immediately** while
:class:`~vantage_api.jobs.executor.execute_upload_job` runs in a **background thread**
(:class:`fastapi.BackgroundTasks` + :func:`starlette.concurrency.run_in_threadpool`).

The preprocessing pipeline lives under ``vantage_preprocess``; see
:func:`~vantage_preprocess.services.pipeline.run_batch` and :func:`~vantage_api.processing.runner.run_upload_job`.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from vantage_api.deps import get_api_settings
from vantage_api.jobs.executor import execute_upload_job
from vantage_api.jobs.store import JobRecord, get_job_store
from vantage_api.schemas import JobProgress, JobQualitySummary, JobStatusResponse, UploadAcceptedResponse
from vantage_api.settings import ApiSettings
from vantage_preprocess.config import ChunkPolicy, IntakeLimits, PipelineConfig

logger = logging.getLogger(__name__)

router = APIRouter()


def _allowed_suffix(name: str) -> bool:
    suf = Path(name).suffix.lower()
    return suf in (".pdf", ".docx", ".txt")


def _safe_name(raw: str | None, index: int) -> str:
    if not raw:
        return f"upload_{index}.txt"
    if "/" in raw or "\\" in raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )
    base = Path(raw).name
    if not base or base in (".", ".."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )
    return base


def _pipeline_config(settings: ApiSettings) -> PipelineConfig:
    return PipelineConfig(
        intake=IntakeLimits(
            max_bytes=settings.max_upload_bytes,
            allowed_suffixes=frozenset({".pdf", ".docx", ".txt"}),
        ),
        chunk=ChunkPolicy(sizing=settings.chunking_model()),
    )


@router.post(
    "/upload-and-process",
    summary="Upload files and start preprocessing (non-blocking)",
    response_model=UploadAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_and_process(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(
        ...,
        description="One or more PDF, DOCX, or TXT files",
    ),
    include_xlsx: bool = Query(
        True,
        description="Include vantage_chunks.xlsx in the output ZIP (default: true).",
    ),
    settings: ApiSettings = Depends(get_api_settings),
) -> UploadAcceptedResponse:
    """
    Accept multipart uploads, save inputs, enqueue extraction → chunking → export, return ``job_id``.

    Poll ``GET /status/{job_id}`` until ``status`` is ``complete`` or ``failed``, then
    ``GET /download/{job_id}`` for the ZIP (CSV, JSONL, XLSX when enabled, processing report, …).
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if len(files) > settings.max_files_per_job:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files (max {settings.max_files_per_job})",
        )

    blobs: list[tuple[str, bytes]] = []
    for i, uf in enumerate(files):
        name = _safe_name(uf.filename, i)
        if not _allowed_suffix(name):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported type for {name!r}; allowed: .pdf, .docx, .txt",
            )
        data = await uf.read()
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File {name!r} exceeds max size ({settings.max_upload_bytes} bytes)",
            )
        blobs.append((name, data))

    job_id = uuid.uuid4().hex
    work_root = Path(settings.data_dir).resolve() / "jobs" / job_id
    inputs_dir = work_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []
    for i, (name, data) in enumerate(blobs):
        dest = inputs_dir / f"{i:03d}_{name}"
        dest.write_bytes(data)
        saved_paths.append(dest)

    cfg = _pipeline_config(settings)
    store = get_job_store()
    store.put(
        JobRecord(
            job_id=job_id,
            status="processing",
            work_dir=work_root,
            files_total=len(saved_paths),
            files_processed=0,
            chunks_created=0,
        ),
    )

    async def _run_pipeline() -> None:
        await run_in_threadpool(
            execute_upload_job,
            job_id=job_id,
            input_paths=saved_paths,
            work_dir=work_root,
            pipeline_config=cfg,
            include_xlsx=include_xlsx,
        )

    background_tasks.add_task(_run_pipeline)

    logger.info("Job %s accepted (%s file(s)); processing in background", job_id, len(saved_paths))

    return UploadAcceptedResponse(
        job_id=job_id,
        status="processing",
        message=f"Processing started. Poll GET /status/{job_id} until complete.",
        status_url=f"/status/{job_id}",
    )


def _quality_summary_from_report(report: dict[str, Any] | None) -> JobQualitySummary | None:
    if not report:
        return None
    raw = report.get("quality_summary")
    if raw is None:
        return None
    return JobQualitySummary.model_validate(raw)


def _status_to_response(rec: JobRecord) -> JobStatusResponse:
    prog = JobProgress(
        files_processed=rec.files_processed,
        files_total=rec.files_total,
        chunks_created=rec.chunks_created,
    )
    err_list = list(rec.summary.errors) if rec.summary is not None else []
    qsum = _quality_summary_from_report(rec.processing_report) if rec.status == "complete" else None
    return JobStatusResponse(
        job_id=rec.job_id,
        status=rec.status,  # type: ignore[arg-type]
        progress=prog,
        chunks_created=rec.chunks_created,
        errors=err_list,
        created_at=rec.created_at,
        finished_at=rec.finished_at,
        summary=rec.summary,
        quality_summary=qsum,
        download_path=f"/download/{rec.job_id}" if rec.zip_path else None,
        message=rec.message,
    )


@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    summary="Poll job status, progress, and errors",
)
def get_status(job_id: str) -> JobStatusResponse:
    rec = get_job_store().get(job_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return _status_to_response(rec)


@router.get(
    "/download/{job_id}",
    summary="Download the ZIP bundle for a complete job",
    responses={
        409: {"description": "Job still running or failed without artifacts"},
        404: {"description": "Unknown job_id"},
    },
)
def download_job(job_id: str) -> FileResponse:
    rec = get_job_store().get(job_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    if rec.status == "processing" or rec.status == "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job not finished yet; poll GET /status/{job_id}",
        )
    if rec.status == "failed" or not rec.zip_path or not rec.zip_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ZIP not available (job failed or artifacts missing).",
        )
    return FileResponse(
        path=rec.zip_path,
        filename=f"vantage-job-{job_id}.zip",
        media_type="application/zip",
    )
