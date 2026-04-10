"""Batch pipeline: per-file outcomes and combined rows."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from vantage_preprocess.config import ChunkPolicy, IntakeLimits, PipelineConfig
from vantage_preprocess.services.pipeline import run_batch


def test_run_batch_records_per_file(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("PART 1 - GENERAL\n\n" + "word " * 600, encoding="utf-8")
    b.write_text("SECTION 02 41 00\n\n" + "x " * 600, encoding="utf-8")

    cfg = PipelineConfig(
        intake=IntakeLimits(
            max_bytes=10_000_000,
            allowed_suffixes=frozenset({".txt"}),
        ),
        chunk=ChunkPolicy(),
    )
    started = datetime.now(UTC)
    batch = run_batch([a, b], cfg, run_id="run1", started_at=started)
    assert len(batch.per_file) == 2
    assert all(p.success for p in batch.per_file)
    assert batch.files_processed_ok == 2
    assert batch.failure_count == 0
    assert batch.rows_written >= 1
