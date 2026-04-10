"""Browser UI static files are mounted at /ui when assets are present."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from vantage_api.app import _discover_web_dir, create_app


def test_discover_web_dir_finds_package_assets() -> None:
    d = _discover_web_dir()
    assert d is not None
    assert (d / "index.html").is_file()
    assert (d / "app.js").is_file()


def test_ui_routes() -> None:
    client = TestClient(create_app())
    r = client.get("/ui", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers.get("location") == "/ui/"
    r2 = client.get("/ui/")
    assert r2.status_code == 200
    assert "<!DOCTYPE html>" in r2.text
