from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from vantage_preprocess.chunking.config import ChunkingConfig


class IntakeLimits(BaseModel):
    """Validation rules for file intake."""

    max_bytes: int | None = Field(
        default=500 * 1024 * 1024,
        description="Maximum file size (None = no limit)",
    )
    allowed_suffixes: frozenset[str] | None = Field(
        default=None,
        description="If set, only these suffixes (lowercase, with dot) are accepted",
    )


class ChunkPolicy(BaseModel):
    """Batch-level chunking policy (word bounds + overlap)."""

    sizing: ChunkingConfig = Field(default_factory=ChunkingConfig)
    combined_basename: str = "vantage_chunks"


class PipelineConfig(BaseModel):
    """Top-level settings for one batch run."""

    intake: IntakeLimits = Field(default_factory=IntakeLimits)
    chunk: ChunkPolicy = Field(default_factory=ChunkPolicy)
    input_path: Path | None = None
    out_dir: Path | None = None
    formats: list[str] = Field(default_factory=lambda: ["jsonl", "csv"])
    recursive: bool = False
