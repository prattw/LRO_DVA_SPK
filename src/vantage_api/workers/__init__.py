"""
Placeholder for background workers (Celery, RQ, Dramatiq).

The API currently runs :func:`~vantage_api.processing.runner.run_upload_job` in a thread pool
(:func:`starlette.concurrency.run_in_threadpool`). To move work off the request thread:

1. Enqueue a task with ``job_id`` and paths under ``VANTAGE_DATA_DIR/jobs/{job_id}``.
2. Return ``202 Accepted`` with ``job_id`` and poll ``GET /status/{job_id}``.
3. Worker calls the same ``run_upload_job`` and updates shared job state (Redis/DB).
"""
