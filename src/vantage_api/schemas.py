"""Pydantic models for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

JobLifecycleStatus = Literal["pending", "processing", "complete", "failed"]


class FileProcessingError(BaseModel):
    """Structured error for one input file (pipeline continued for other files)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    source_filename: str
    stage: str
    message: str
    document_id: str | None = None
    detail: str | None = None


class PerFileResult(BaseModel):
    """Outcome for one uploaded file within a batch."""

    filename: str
    success: bool
    document_id: str | None = None
    chunks: int = Field(default=0, ge=0)
    failure_stage: str | None = None
    error_message: str | None = None


class ProcessingSummary(BaseModel):
    """Aggregate stats after a batch job completes."""

    files_submitted: int = Field(ge=0, description="Files in the multipart request.")
    files_processed_ok: int = Field(
        ge=0,
        description="Files that completed extraction+chunking without error.",
    )
    failures: int = Field(ge=0, description="Count of files that failed (intake or extract).")
    chunks_created: int = Field(ge=0, description="Total chunk rows across successful files.")
    errors: list[FileProcessingError] = Field(
        default_factory=list,
        description="Structured errors (one per failed file, when available).",
    )
    per_file: list[PerFileResult] = Field(
        default_factory=list,
        description="Parallel list to uploads: success flag and chunk counts per file.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal notices (e.g. validation hints from chunking).",
    )


class JobQualitySummary(BaseModel):
    """
    Aggregated extraction/chunk quality for the job (mirrors ``processing_report.json`` → ``quality_summary``).

    Per-chunk fields (``chunk_quality_score``, ``low_quality_chunk``, …) are in the CSV/JSONL/XLSX exports.
    """

    chunks_total: int = Field(ge=0)
    low_quality_chunks: int = Field(ge=0)
    documents_needing_review: int = Field(
        ge=0,
        description="Count of distinct source documents flagged for review.",
    )
    mean_chunk_quality_score: float | None = Field(
        default=None,
        description="Mean heuristic score across chunks; null if no chunks.",
    )
    fraction_low_quality: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Share of chunks marked low-quality.",
    )


class JobProgress(BaseModel):
    """Coarse progress for polling UIs (updated after each input file finishes)."""

    files_processed: int = Field(ge=0, description="Input files finished (success or failure).")
    files_total: int = Field(ge=0, description="Input files in this job.")
    chunks_created: int = Field(
        ge=0,
        description="Cumulative chunk rows emitted so far; final total when status is complete.",
    )


class UploadAcceptedResponse(BaseModel):
    """Immediate response from POST /upload-and-process (processing runs in the background)."""

    job_id: str
    status: Literal["processing"] = Field(
        description="Job was accepted; poll GET /status/{job_id} until complete or failed.",
    )
    message: str = Field(default="Processing started.")
    status_url: str = Field(description="Relative URL to poll, e.g. /status/{job_id}.")


class JobStatusResponse(BaseModel):
    """GET /status/{job_id}."""

    job_id: str
    status: JobLifecycleStatus
    progress: JobProgress
    chunks_created: int = Field(
        ge=0,
        description="Same as progress.chunks_created (convenience for simple clients).",
    )
    errors: list[FileProcessingError] = Field(
        default_factory=list,
        description="Populated when the job is complete (or empty); mirrors summary.errors.",
    )
    created_at: datetime
    finished_at: datetime | None = None
    summary: ProcessingSummary | None = Field(
        default=None,
        description="Full batch summary when status is complete.",
    )
    quality_summary: JobQualitySummary | None = Field(
        default=None,
        description="Heuristic quality aggregates when the job finished successfully (null while running or if unavailable).",
    )
    download_path: str | None = Field(
        default=None,
        description="Relative URL to the ZIP when status is complete.",
    )
    message: str | None = Field(
        default=None,
        description="Fatal error message when status is failed.",
    )
