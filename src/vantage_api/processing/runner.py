"""
Run the full preprocessing pipeline for saved upload paths.

This module is **API-agnostic**: FastAPI routes should call :func:`run_upload_job` with paths on
disk. A future worker can import the same function without importing FastAPI.
"""

from __future__ import annotations

import json
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from collections.abc import Callable
from pathlib import Path
from typing import Any

from vantage_api.processing.batch_processor import process_upload_batch
from vantage_preprocess.config import PipelineConfig
from vantage_preprocess.models.result import BatchResult
from vantage_preprocess.quality.scoring import summarize_job_quality
from vantage_preprocess.services.batch_reports import (
    write_errors_report_json,
    write_per_file_results_json,
)
from vantage_preprocess.services.pipeline import write_batch_artifacts

logger = logging.getLogger(__name__)


@dataclass
class JobExecutionResult:
    """Outcome of :func:`run_upload_job` (used to build HTTP responses and ZIP)."""

    batch: BatchResult
    work_dir: Path
    output_dir: Path
    manifest_path: Path
    zip_path: Path
    processing_report: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


def run_upload_job(
    *,
    job_id: str,
    input_paths: list[Path],
    work_dir: Path,
    pipeline_config: PipelineConfig,
    include_xlsx: bool = True,
    on_file_done: Callable[[int, int, int], None] | None = None,
) -> JobExecutionResult:
    """
    Execute intake → extract → section detection → chunking → export artifacts → ZIP.

    ``input_paths`` must be existing files (already validated and saved by the API layer).
    """
    if not input_paths:
        raise ValueError("input_paths must not be empty")

    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir = work_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    formats = ["jsonl", "csv"]
    if include_xlsx:
        formats.append("xlsx")

    logger.info("Job %s: processing %s file(s)", job_id, len(input_paths))

    batch = process_upload_batch(
        input_paths,
        pipeline_config,
        job_id=job_id,
        on_file_done=on_file_done,
    )

    manifest_path = write_batch_artifacts(
        batch,
        output_dir,
        formats,
        combined_basename="vantage_chunks",
        input_display=f"job:{job_id}",
    )
    write_per_file_results_json(output_dir, batch)
    write_errors_report_json(output_dir, batch)

    warnings: list[str] = []
    processing_report = _build_processing_report(
        job_id=job_id,
        batch=batch,
        input_paths=input_paths,
        warnings=warnings,
    )
    report_path = work_dir / "processing_report.json"
    report_path.write_text(json.dumps(processing_report, indent=2), encoding="utf-8")

    metadata = _build_job_metadata(job_id, input_paths, pipeline_config, include_xlsx)
    meta_path = work_dir / "job_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    zip_path = _zip_outputs(work_dir, job_id, output_dir, report_path, meta_path)

    return JobExecutionResult(
        batch=batch,
        work_dir=work_dir,
        output_dir=output_dir,
        manifest_path=manifest_path,
        zip_path=zip_path,
        processing_report=processing_report,
        warnings=warnings,
    )


def _build_processing_report(
    *,
    job_id: str,
    batch: BatchResult,
    input_paths: list[Path],
    warnings: list[str],
) -> dict[str, Any]:
    err_payload = [e.model_dump(mode="json") for e in batch.errors]
    ok_files = batch.files_seen - len(batch.errors)
    per_payload = [p.model_dump(mode="json") for p in batch.per_file]
    return {
        "job_id": job_id,
        "schema": "vantage_processing_report_v3",
        "started_at": batch.started_at.isoformat(),
        "finished_at": batch.finished_at.isoformat(),
        "input_files": [p.name for p in input_paths],
        "summary": {
            "files_submitted": len(input_paths),
            "files_processed_ok": max(0, ok_files),
            "failures": batch.failure_count,
            "chunks_created": batch.rows_written,
            "errors": err_payload,
            "per_file": per_payload,
        },
        "quality_summary": summarize_job_quality(batch.rows),
        "warnings": warnings,
        "chunking": {
            "note": (
                "Chunks use the section-aware chunker with word limits and overlap; "
                "see vantage_preprocess.chunking."
            ),
        },
    }


def _build_job_metadata(
    job_id: str,
    input_paths: list[Path],
    config: PipelineConfig,
    include_xlsx: bool,
) -> dict[str, Any]:
    chunk = config.chunk.sizing.model_dump()
    return {
        "job_id": job_id,
        "created_at": datetime.now(UTC).isoformat(),
        "input_files": [p.name for p in input_paths],
        "include_xlsx": include_xlsx,
        "pipeline": {
            "intake_max_bytes": config.intake.max_bytes,
            "chunk_sizing": chunk,
        },
    }


def _zip_outputs(
    work_dir: Path,
    job_id: str,
    output_dir: Path,
    report_path: Path,
    meta_path: Path,
) -> Path:
    zip_path = work_dir / f"{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(output_dir.iterdir()):
            if f.is_file():
                zf.write(f, arcname=f"output/{f.name}")
        zf.write(report_path, arcname="processing_report.json")
        zf.write(meta_path, arcname="job_metadata.json")
    logger.info("Job %s: wrote %s", job_id, zip_path)
    return zip_path
