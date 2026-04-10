"""Pipeline edge cases: empty files, corrupted PDFs, batch isolation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from vantage_preprocess.config import ChunkPolicy, IntakeLimits, PipelineConfig
from vantage_preprocess.services.pipeline import run_batch

pytestmark = pytest.mark.integration


def test_empty_txt_yields_zero_chunks_success(tmp_path: Path) -> None:
    p = tmp_path / "empty.txt"
    p.write_bytes(b"")
    cfg = PipelineConfig(
        intake=IntakeLimits(max_bytes=1_000_000, allowed_suffixes=frozenset({".txt"})),
        chunk=ChunkPolicy(),
    )
    batch = run_batch([p], cfg, run_id="e", started_at=datetime.now(UTC))
    assert batch.failure_count == 0
    assert batch.rows_written == 0
    assert batch.per_file[0].success is True


def test_corrupted_pdf_fails_at_extract(tmp_path: Path) -> None:
    p = tmp_path / "bad.pdf"
    p.write_bytes(b"%PDF-1.4\nnot a real pdf")
    cfg = PipelineConfig(
        intake=IntakeLimits(max_bytes=1_000_000, allowed_suffixes=frozenset({".pdf"})),
        chunk=ChunkPolicy(),
    )
    batch = run_batch([p], cfg, run_id="x", started_at=datetime.now(UTC))
    assert batch.failure_count == 1
    assert batch.rows_written == 0
    pf = batch.per_file[0]
    assert pf.success is False
    assert pf.failure_stage == "extract"
    assert pf.error_message


def test_batch_one_failure_other_ok(tmp_path: Path) -> None:
    good = tmp_path / "good.txt"
    good.write_text("PART 1\n\n" + "word " * 500, encoding="utf-8")
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF broken")

    cfg = PipelineConfig(
        intake=IntakeLimits(
            max_bytes=10_000_000,
            allowed_suffixes=frozenset({".txt", ".pdf"}),
        ),
        chunk=ChunkPolicy(),
    )
    batch = run_batch([good, bad], cfg, run_id="mix", started_at=datetime.now(UTC))
    assert len(batch.per_file) == 2
    assert batch.per_file[0].success is True
    assert batch.per_file[1].success is False
    assert batch.rows_written >= 1
