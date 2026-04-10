"""FastAPI application factory."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from vantage_api.routes import health, jobs

logger = logging.getLogger(__name__)


def _discover_web_dir() -> Path | None:
    """
    Locate the folder that contains ``index.html`` for the browser UI.

    Resolution order (first match wins):
    1. ``vantage_api.web`` package directory (works with ``pip install`` and ``pip install -e``).
    2. ``vantage_api/web`` next to this ``app.py`` file.
    3. ``$VANTAGE_WEB_DIR`` if set.
    4. Repository-root ``web/`` (two levels above ``app.py`` in a ``src/`` layout).
    5. ``./web`` under the current working directory.
    """
    candidates: list[Path] = []

    try:
        import vantage_api.web as web_pkg

        pkg_dir = Path(web_pkg.__file__).resolve().parent
        candidates.append(pkg_dir)
    except Exception as e:
        logger.debug("Could not import vantage_api.web for UI path: %s", e)

    app_dir = Path(__file__).resolve().parent
    candidates.append(app_dir / "web")

    ev = os.environ.get("VANTAGE_WEB_DIR")
    if ev:
        candidates.insert(0, Path(ev))

    candidates.append(app_dir.parents[2] / "web")
    candidates.append(Path.cwd() / "web")

    seen: set[str] = set()
    unique: list[Path] = []
    for c in candidates:
        key = str(c.resolve()) if c.exists() else str(c)
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)

    for c in unique:
        index = c / "index.html"
        if c.is_dir() and index.is_file():
            logger.info("Serving browser UI from %s", c)
            return c

    logger.warning(
        "Browser UI not mounted: no directory with index.html. Checked: %s",
        [str(p) for p in unique],
    )
    return None


def create_app() -> FastAPI:
    """Create the ASGI app. Routers register here; avoid heavy imports at module level."""
    web_dir = _discover_web_dir()

    app = FastAPI(
        title="Army Vantage Preprocess API",
        description=(
            "**Non-blocking uploads:** `POST /upload-and-process` returns `202` with a `job_id` "
            "immediately; poll `GET /status/{job_id}` for progress and errors, then "
            "`GET /download/{job_id}` for the ZIP (CSV, JSONL, XLSX, processing report). "
            "Poll responses include optional **quality_summary** (aggregates; per-chunk scores are in exports). "
            "Pipeline: ``vantage_preprocess`` extraction → section detection → chunking. "
            "See ``docs/API_ARMY_VANTAGE.md`` for curl examples."
        ),
        version="0.3.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register /ui *before* other routes so `/ui` is not swallowed by catch-alls (defensive).
    if web_dir is not None:

        @app.get("/ui", include_in_schema=False)
        def _ui_no_trailing_slash() -> RedirectResponse:
            return RedirectResponse(url="/ui/", status_code=307)

        app.mount(
            "/ui",
            StaticFiles(directory=str(web_dir), html=True),
            name="web_ui",
        )

    @app.get("/", tags=["meta"], summary="Service index")
    def root() -> dict[str, str | dict[str, str]]:
        """JSON discovery for humans and scripts (the interactive UI is at ``/docs``)."""
        payload: dict[str, str | dict[str, str]] = {
            "service": "Army Vantage Preprocess API",
            "version": "0.3.0",
            "docs": "/docs",
            "openapi_json": "/openapi.json",
            "health": "/health",
            "endpoints": {
                "upload_and_process": "POST /upload-and-process",
                "status": "GET /status/{job_id}",
                "download": "GET /download/{job_id}",
            },
        }
        if web_dir is not None:
            payload["web_ui"] = "/ui/"
        return payload

    app.include_router(health.router, tags=["health"])
    app.include_router(jobs.router, tags=["jobs"])

    return app
