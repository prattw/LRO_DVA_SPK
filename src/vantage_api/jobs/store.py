"""In-memory job index with on-disk artifacts (replace with Redis + object storage later)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vantage_api.schemas import FileProcessingError, ProcessingSummary


@dataclass
class JobRecord:
    """Server-side job state for polling and download."""

    job_id: str
    status: str  # pending | processing | complete | failed
    work_dir: Path
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    zip_path: Path | None = None
    summary: ProcessingSummary | None = None
    message: str | None = None
    processing_report: dict[str, Any] | None = None
    files_total: int = 0
    files_processed: int = 0
    chunks_created: int = 0


class JobStore:
    """Thread-safe registry keyed by job_id."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, JobRecord] = {}

    def put(self, record: JobRecord) -> None:
        with self._lock:
            self._jobs[record.job_id] = record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs: Any) -> None:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return
            for k, v in kwargs.items():
                setattr(rec, k, v)

    def clear(self) -> None:
        """Test helper: drop all jobs."""
        with self._lock:
            self._jobs.clear()


_store: JobStore | None = None


def get_job_store() -> JobStore:
    global _store
    if _store is None:
        _store = JobStore()
    return _store


def errors_to_file_errors(errors: list[Any]) -> list[FileProcessingError]:
    out: list[FileProcessingError] = []
    for e in errors:
        d = e.model_dump() if hasattr(e, "model_dump") else e
        out.append(
            FileProcessingError(
                source_filename=d.get("source_filename") or "",
                stage=d.get("stage") or "unknown",
                message=d.get("message") or "",
                document_id=d.get("document_id"),
                detail=d.get("detail"),
            ),
        )
    return out
