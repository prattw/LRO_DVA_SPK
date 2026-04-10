"""Fixtures for integration tests (API + pipeline)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """
    FastAPI TestClient with isolated job store and data dir.

    Sets ``VANTAGE_DATA_DIR`` under ``tmp_path`` so uploads do not touch real ``./var/vantage``.
    """
    monkeypatch.setenv("VANTAGE_DATA_DIR", str(tmp_path))

    from vantage_api.deps import clear_settings_cache
    from vantage_api.jobs.store import get_job_store

    clear_settings_cache()
    get_job_store().clear()

    from fastapi.testclient import TestClient

    from vantage_api.app import create_app

    return TestClient(create_app())
