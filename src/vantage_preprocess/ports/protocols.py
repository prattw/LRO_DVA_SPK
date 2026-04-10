from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from vantage_preprocess.config import IntakeLimits, PipelineConfig
from vantage_preprocess.models.document import StructuredDocument
from vantage_preprocess.models.intake import IntakeRecord
from vantage_preprocess.models.result import BatchResult


@runtime_checkable
class IntakeService(Protocol):
    def intake_from_path(self, path: Path, limits: IntakeLimits) -> IntakeRecord: ...


@runtime_checkable
class DocumentDetector(Protocol):
    def guess_kind(self, path: Path) -> str: ...


@runtime_checkable
class TextExtractionService(Protocol):
    def extract_structured(self, intake: IntakeRecord) -> StructuredDocument: ...


@runtime_checkable
class PipelineRunner(Protocol):
    """Sync orchestration used by CLI and (via thread/worker) web API."""

    def run_paths(
        self,
        paths: list[Path],
        config: PipelineConfig,
        run_id: str,
        started_at: datetime,
    ) -> BatchResult: ...
