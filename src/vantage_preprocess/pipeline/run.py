from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from vantage_preprocess.chunking.config import ChunkingConfig
from vantage_preprocess.config import ChunkPolicy, PipelineConfig
from vantage_preprocess.models.result import BatchResult
from vantage_preprocess.services.pipeline import (
    collect_paths,
    run_batch,
    write_batch_artifacts,
)
from vantage_preprocess.utils.ids import run_manifest_id


@dataclass
class RunResult:
    """CLI-friendly view of a batch run (manifest path + full `BatchResult`)."""

    manifest_path: Path
    batch: BatchResult

    @property
    def files_processed(self) -> int:
        return self.batch.files_processed_ok

    @property
    def rows_written(self) -> int:
        return self.batch.rows_written

    @property
    def errors(self) -> list[str]:
        lines = []
        for e in self.batch.errors:
            prefix = f"{e.source_filename}: " if e.source_filename else ""
            lines.append(f"{prefix}[{e.stage}] {e.message}")
        return lines


def run_pipeline(
    input_path: Path,
    out_dir: Path,
    formats: list[str],
    recursive: bool = False,
    chunking: ChunkingConfig | None = None,
    combined_basename: str = "vantage_chunks",
) -> RunResult:
    """High-level entry: collect files → run sync pipeline → write exports + manifest."""
    sizing = chunking or ChunkingConfig()
    config = PipelineConfig(
        chunk=ChunkPolicy(sizing=sizing, combined_basename=combined_basename),
    )
    paths = collect_paths(input_path, recursive)
    run_id = run_manifest_id()
    started = datetime.now(UTC)
    batch = run_batch(paths, config, run_id=run_id, started_at=started)
    batch = batch.model_copy(
        update={
            "input_resolved": str(input_path.resolve()),
            "out_dir": str(out_dir.resolve()),
        },
    )
    manifest_path = write_batch_artifacts(
        batch,
        out_dir,
        formats,
        combined_basename=combined_basename,
        input_display=str(input_path.resolve()),
    )
    return RunResult(manifest_path=manifest_path, batch=batch)
