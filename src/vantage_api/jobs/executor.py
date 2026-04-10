"""
Blocking job execution for API uploads.

Call :func:`execute_upload_job` from a worker thread (see FastAPI ``BackgroundTasks`` +
:func:`starlette.concurrency.run_in_threadpool`). The HTTP layer only saves inputs and enqueues work;
this module owns pipeline invocation and :class:`~vantage_api.jobs.store.JobStore` updates so a
future Celery/RQ worker can import the same function unchanged.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from vantage_api.jobs.store import errors_to_file_errors, get_job_store
from vantage_api.processing.runner import run_upload_job
from vantage_api.schemas import PerFileResult, ProcessingSummary
from vantage_preprocess.config import PipelineConfig

logger = logging.getLogger(__name__)


def execute_upload_job(
    *,
    job_id: str,
    input_paths: list[Path],
    work_dir: Path,
    pipeline_config: PipelineConfig,
    include_xlsx: bool = True,
) -> None:
    """
    Run extraction → chunking → export → ZIP, updating the in-memory job store as the batch runs.

    Raises nothing: failures are recorded on the job as ``status=failed``.
    """
    store = get_job_store()
    total_files = len(input_paths)

    def on_file_done(files_done: int, files_total: int, cumulative_chunks: int) -> None:
        store.update(
            job_id,
            files_processed=files_done,
            files_total=files_total,
            chunks_created=cumulative_chunks,
        )

    try:
        store.update(
            job_id,
            status="processing",
            files_total=total_files,
            files_processed=0,
            chunks_created=0,
        )
        result = run_upload_job(
            job_id=job_id,
            input_paths=input_paths,
            work_dir=work_dir,
            pipeline_config=pipeline_config,
            include_xlsx=include_xlsx,
            on_file_done=on_file_done,
        )
        batch = result.batch
        file_errors = errors_to_file_errors(batch.errors)
        per_file = [
            PerFileResult(
                filename=p.source_filename,
                success=p.success,
                document_id=p.document_id,
                chunks=p.chunks_created,
                failure_stage=p.failure_stage,
                error_message=p.error_message,
            )
            for p in batch.per_file
        ]
        summary = ProcessingSummary(
            files_submitted=len(input_paths),
            files_processed_ok=batch.files_processed_ok,
            failures=batch.failure_count,
            chunks_created=batch.rows_written,
            errors=file_errors,
            per_file=per_file,
            warnings=result.warnings,
        )
        store.update(
            job_id,
            status="complete",
            finished_at=batch.finished_at,
            zip_path=result.zip_path,
            summary=summary,
            processing_report=result.processing_report,
            files_processed=batch.files_seen,
            files_total=batch.files_seen,
            chunks_created=batch.rows_written,
        )
        logger.info(
            "Job %s finished: chunks=%s files_ok=%s",
            job_id,
            batch.rows_written,
            batch.files_processed_ok,
        )
    except Exception as e:
        logger.exception("Job %s failed", job_id)
        store.update(
            job_id,
            status="failed",
            message=str(e),
            finished_at=datetime.now(UTC),
        )
