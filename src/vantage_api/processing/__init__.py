"""Synchronous job execution (swap for a Celery/RQ task later)."""

from vantage_api.processing.batch_processor import process_upload_batch
from vantage_api.processing.runner import JobExecutionResult, run_upload_job

__all__ = ["JobExecutionResult", "process_upload_batch", "run_upload_job"]
