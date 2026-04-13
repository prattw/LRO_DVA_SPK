"""Job upload API (requires ``[api]`` extra)."""

from __future__ import annotations

import io
import time
import zipfile

import pytest

pytest.importorskip("multipart")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from vantage_api.app import create_app
from vantage_api.deps import clear_settings_cache
from vantage_api.jobs.store import get_job_store


def _wait_for_terminal(client: TestClient, job_id: str, *, timeout_s: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout_s
    last: dict = {}
    while time.monotonic() < deadline:
        st = client.get(f"/status/{job_id}")
        assert st.status_code == 200, st.text
        last = st.json()
        if last["status"] in ("complete", "failed"):
            return last
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} did not finish: {last!r}")


def test_upload_process_txt_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("VANTAGE_DATA_DIR", str(tmp_path))
    clear_settings_cache()
    get_job_store().clear()

    client = TestClient(create_app())
    content = b"PART 1 - GENERAL\n\nSome body text for chunking.\n" * 80
    r = client.post(
        "/upload-and-process",
        files=[("files", ("sample.txt", io.BytesIO(content), "text/plain"))],
    )
    assert r.status_code == 202, r.text
    data = r.json()
    assert data["status"] == "processing"
    assert data["job_id"]
    assert "/status/" in data["status_url"]

    jid = data["job_id"]
    final = _wait_for_terminal(client, jid)
    assert final["status"] == "complete"
    assert final["progress"]["files_total"] == 1
    assert final["progress"]["files_processed"] == 1
    assert final["chunks_created"] >= 1
    assert final["summary"] is not None
    assert final["summary"]["chunks_created"] >= 1
    assert final["summary"]["files_submitted"] == 1
    assert final["summary"]["failures"] == 0
    assert len(final["summary"]["per_file"]) == 1
    assert final["summary"]["per_file"][0]["success"] is True
    assert final["download_path"] == f"/download/{jid}"
    qs = final.get("quality_summary")
    assert qs is not None
    assert "chunks_total" in qs and qs["chunks_total"] >= 1

    st = client.get(f"/status/{jid}")
    assert st.status_code == 200
    assert st.json()["job_id"] == jid

    dl = client.get(f"/download/{jid}")
    assert dl.status_code == 200
    assert "zip" in dl.headers.get("content-type", "")
    zf = zipfile.ZipFile(io.BytesIO(dl.content))
    names = zf.namelist()
    assert "processing_report.json" in names
    assert any(n.endswith("vantage_chunks.jsonl") for n in names)
    assert any(n.endswith("vantage_chunks.csv") for n in names)
    assert any(n.endswith("vantage_master.jsonl") for n in names)
    assert any(n.endswith("vantage_master.csv") for n in names)
    assert any(n.endswith("vantage_chunks.xlsx") for n in names)
    assert any(n.endswith("per_file_results.json") for n in names)
    assert any(n.endswith("errors_report.json") for n in names)

    clear_settings_cache()


def test_download_not_ready_returns_409(tmp_path, monkeypatch) -> None:
    """GET /download before the job completes returns 409 (not 404 for known job_ids)."""
    monkeypatch.setenv("VANTAGE_DATA_DIR", str(tmp_path))
    clear_settings_cache()
    get_job_store().clear()

    from pathlib import Path

    from vantage_api.jobs.store import JobRecord

    jid = "ab" * 16
    work_dir = Path(tmp_path) / "jobs" / jid
    work_dir.mkdir(parents=True)
    get_job_store().put(
        JobRecord(
            job_id=jid,
            status="processing",
            work_dir=work_dir,
            files_total=1,
            files_processed=0,
        ),
    )
    client = TestClient(create_app())
    dl = client.get(f"/download/{jid}")
    assert dl.status_code == 409


def test_reject_bad_extension(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("VANTAGE_DATA_DIR", str(tmp_path))
    clear_settings_cache()

    client = TestClient(create_app())
    r = client.post(
        "/upload-and-process",
        files=[("files", ("bad.bin", io.BytesIO(b"x"), "application/octet-stream"))],
    )
    assert r.status_code == 400

    clear_settings_cache()
