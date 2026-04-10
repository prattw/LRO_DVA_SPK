"""FastAPI: upload, status polling, download gating."""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("multipart")

from tests.test_api_jobs import _wait_for_terminal

pytestmark = [pytest.mark.integration, pytest.mark.api]


def test_upload_returns_202_with_job_id(api_client) -> None:
    body = b"PART 1\n\n" + b"word " * 400
    r = api_client.post(
        "/upload-and-process",
        files=[("files", ("chunk_me.txt", io.BytesIO(body), "text/plain"))],
    )
    assert r.status_code == 202, r.text
    data = r.json()
    assert "job_id" in data and len(data["job_id"]) >= 8
    assert data["status"] == "processing"
    assert "/status/" in data["status_url"]


def test_status_unknown_job_404(api_client) -> None:
    r = api_client.get("/status/" + "0" * 32)
    assert r.status_code == 404


def test_poll_until_complete_and_zip_has_exports(api_client) -> None:
    content = b"SECTION A\n\n" + b"Some chunkable body text. " * 120
    up = api_client.post(
        "/upload-and-process",
        files=[("files", ("sample.txt", io.BytesIO(content), "text/plain"))],
    )
    assert up.status_code == 202
    job_id = up.json()["job_id"]

    final = _wait_for_terminal(api_client, job_id, timeout_s=60.0)
    assert final["status"] == "complete"
    assert final["progress"]["files_total"] == 1
    assert final.get("quality_summary") is not None

    dl = api_client.get(f"/download/{job_id}")
    assert dl.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(dl.content))
    names = zf.namelist()
    assert any(n.endswith("vantage_chunks.csv") for n in names)
    assert any(n.endswith("processing_report.json") for n in names)
    assert any("vantage_portal_txt/" in n and n.endswith(".txt") for n in names)


def test_download_while_processing_returns_409(api_client) -> None:
    from vantage_api.jobs.store import JobRecord, get_job_store

    jid = "cd" * 16
    data_dir = Path(os.environ["VANTAGE_DATA_DIR"])
    job_dir = data_dir / "jobs" / jid
    job_dir.mkdir(parents=True, exist_ok=True)
    get_job_store().put(
        JobRecord(
            job_id=jid,
            status="processing",
            work_dir=job_dir,
            files_total=1,
            files_processed=0,
        ),
    )
    r = api_client.get(f"/download/{jid}")
    assert r.status_code == 409
