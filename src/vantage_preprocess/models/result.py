from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from vantage_preprocess.models.document import ExportRow


class ErrorRecord(BaseModel):
    """Non-fatal failure for one document or stage."""

    stage: str
    message: str
    source_filename: str | None = None
    document_id: str | None = None
    detail: str | None = None


class PerFileOutcome(BaseModel):
    """Result of processing one path in a batch (success or failed stage)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    source_filename: str = Field(min_length=1)
    success: bool
    document_id: str | None = None
    chunks_created: int = Field(default=0, ge=0)
    failure_stage: str | None = Field(
        default=None,
        description="intake | extract when success is false",
    )
    error_message: str | None = None


class BatchResult(BaseModel):
    """Outcome of processing a set of paths (CLI batch or API job)."""

    run_id: str
    started_at: datetime
    finished_at: datetime
    rows: list[ExportRow] = Field(default_factory=list)
    errors: list[ErrorRecord] = Field(default_factory=list)
    files_seen: int = 0
    input_resolved: str | None = None
    out_dir: str | None = None
    per_file: list[PerFileOutcome] = Field(
        default_factory=list,
        description="One entry per input path, in order (includes failures).",
    )

    @property
    def rows_written(self) -> int:
        return len(self.rows)

    @property
    def files_processed_ok(self) -> int:
        return self.files_seen - len(self.errors)

    @property
    def failure_count(self) -> int:
        return len(self.errors)
