"""
Upload batch orchestration (API-facing entry).

Delegates to :func:`~vantage_preprocess.services.pipeline.run_batch`, which processes **each file
independently** (failures do not stop other files) and aggregates chunk rows for a single
combined CSV/JSONL/XLSX export.

A future background worker should call :func:`process_upload_batch` the same way the HTTP layer
does.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from vantage_preprocess.config import PipelineConfig
from vantage_preprocess.models.result import BatchResult
from vantage_preprocess.services.pipeline import run_batch

logger = logging.getLogger(__name__)


def process_upload_batch(
    paths: list[Path],
    config: PipelineConfig,
    *,
    job_id: str,
    on_file_done: Callable[[int, int, int], None] | None = None,
) -> BatchResult:
    """
    Run the full pipeline over ``paths`` with structured logging.

    Returns a :class:`~vantage_preprocess.models.result.BatchResult` including ``per_file``
    outcomes and combined ``rows`` for export.
    """
    if not paths:
        raise ValueError("paths must not be empty")

    logger.info(
        "Upload batch job_id=%s: starting %s file(s)",
        job_id,
        len(paths),
    )

    started_at = datetime.now(UTC)
    batch = run_batch(
        paths,
        config,
        run_id=job_id,
        started_at=started_at,
        include_traceback_in_errors=False,
        on_file_done=on_file_done,
    )

    logger.info(
        "Upload batch job_id=%s: finished chunks=%s failures=%s files_ok=%s",
        job_id,
        batch.rows_written,
        batch.failure_count,
        batch.files_processed_ok,
    )
    return batch
