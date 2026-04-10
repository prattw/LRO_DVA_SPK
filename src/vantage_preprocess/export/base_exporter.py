"""Abstract exporter for Army Vantage ingestion formats."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from vantage_preprocess.export.ingestion_record import VantageIngestionRecord
from vantage_preprocess.export.preview import format_ingestion_preview


class BaseVantageExporter(ABC):
    """Protocol for UTF-8 exports with a stable column set."""

    encoding: ClassVar[str] = "utf-8"
    columns: ClassVar[list[str]] = [
        "document_id",
        "source_filename",
        "original_file_type",
        "chunk_id",
        "page_start",
        "page_end",
        "section_title",
        "document_type",
        "extraction_method",
        "extraction_confidence",
        "extraction_mode",
        "ocr_used",
        "ocr_confidence",
        "percent_empty_pages",
        "section_detection_confidence",
        "chunk_quality_score",
        "low_quality_chunk",
        "document_needs_review",
        "chunk_text",
        "processing_timestamp",
    ]

    @abstractmethod
    def write(self, rows: Sequence[VantageIngestionRecord], path: Path) -> None:
        """Write all rows to ``path`` (parent directories created)."""

    def preview_sample(
        self,
        rows: Sequence[VantageIngestionRecord],
        *,
        limit: int = 3,
        chunk_preview_chars: int = 120,
    ) -> str:
        """Human-readable sample for logs or docs (not necessarily valid CSV/JSON)."""
        return format_ingestion_preview(
            rows,
            limit=limit,
            chunk_preview_chars=chunk_preview_chars,
        )
