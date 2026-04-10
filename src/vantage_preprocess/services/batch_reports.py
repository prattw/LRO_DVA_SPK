"""Write per-file and error summary JSON next to combined export artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from vantage_preprocess.models.result import BatchResult


def write_per_file_results_json(out_dir: Path, batch: BatchResult) -> Path | None:
    """Emit ``per_file_results.json`` (one object per input file, in order)."""
    if not batch.per_file:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "per_file_results.json"
    path.write_text(
        json.dumps(
            [p.model_dump(mode="json") for p in batch.per_file],
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def write_errors_report_json(out_dir: Path, batch: BatchResult) -> Path:
    """Emit ``errors_report.json`` for failed files only (mirrors ErrorRecord list)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "errors_report.json"
    payload = {
        "run_id": batch.run_id,
        "failure_count": len(batch.errors),
        "errors": [e.model_dump(mode="json") for e in batch.errors],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
