"""
Canonical row shape for Army Vantage tabular ingestion (CSV / JSONL / XLSX).

Columns align with common data-platform loaders: stable ids, provenance, and chunk payload.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from vantage_preprocess.models.document import ExportRow
    from vantage_preprocess.models.vantage_domain import ExportRecord


def _strip_nul(s: str) -> str:
    return s.replace("\x00", "")


class VantageIngestionRecord(BaseModel):
    """
    One ingest-ready row (field names match typical warehouse column naming).

    ``original_file_type`` is the source file format (pdf, docx, …).
    ``document_type`` is the semantic / detected class for retrieval filters (see
    :class:`~vantage_preprocess.models.vantage_domain.DetectedDocumentKind`).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str = Field(min_length=4)
    source_filename: str = Field(min_length=1, max_length=1024)
    original_file_type: str = Field(description="File format enum value, e.g. pdf, docx.")
    chunk_id: str = Field(min_length=4)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section_title: str | None = Field(default=None, max_length=4000)
    document_type: str = Field(
        description="Semantic document class for Vantage (e.g. unknown, specification_section).",
    )
    extraction_method: str = Field(description="parse, ocr, hybrid, …")
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    extraction_mode: str = Field(
        default="native",
        description="Coarse channel: native | ocr | hybrid.",
    )
    ocr_used: bool = Field(default=False)
    ocr_confidence: float | None = Field(
        default=None,
        description="Mean OCR/hybrid page confidence for this chunk span, if applicable.",
    )
    percent_empty_pages: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Document-level: pages with almost no text.",
    )
    section_detection_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    chunk_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    low_quality_chunk: bool = Field(default=False)
    document_needs_review: bool = Field(default=False)
    chunk_text: str = Field(description="Chunk body for embedding and display.")
    processing_timestamp: datetime = Field(
        description="UTC timestamp when the export row was finalized.",
    )

    @classmethod
    def from_export_row(
        cls,
        row: ExportRow,
        *,
        semantic_document_type: str,
        processing_timestamp: datetime | None = None,
    ) -> Self:
        """Build from pipeline :class:`~vantage_preprocess.models.document.ExportRow`."""
        from vantage_preprocess.models.document import ExportRow as ER

        if not isinstance(row, ER):
            raise TypeError("expected ExportRow")
        ts = processing_timestamp or datetime.now(UTC)
        dt = row.document_type
        oft = dt.value if hasattr(dt, "value") else str(dt)
        em = row.extracted_method
        em_s = em.value if hasattr(em, "value") else str(em)
        return cls(
            document_id=row.document_id,
            source_filename=row.source_filename,
            original_file_type=oft,
            chunk_id=row.chunk_id,
            page_start=row.page_start,
            page_end=row.page_end,
            section_title=row.section_title,
            document_type=semantic_document_type,
            extraction_method=em_s,
            extraction_confidence=row.confidence,
            extraction_mode=row.extraction_mode,
            ocr_used=row.ocr_used,
            ocr_confidence=row.ocr_confidence,
            percent_empty_pages=row.percent_empty_pages,
            section_detection_confidence=row.section_detection_confidence,
            chunk_quality_score=row.chunk_quality_score,
            low_quality_chunk=row.low_quality_chunk,
            document_needs_review=row.document_needs_review,
            chunk_text=_strip_nul(row.chunk_text),
            processing_timestamp=ts,
        )

    @classmethod
    def from_export_record(cls, record: ExportRecord) -> Self:
        """Build from :class:`~vantage_preprocess.models.vantage_domain.ExportRecord`."""
        from vantage_preprocess.models.vantage_domain import ExportRecord as ER

        if not isinstance(record, ER):
            raise TypeError("expected ExportRecord")
        oft = record.original_file_type
        oft_s = oft.value if hasattr(oft, "value") else str(oft)
        em = record.extraction_method
        em_s = em.value if hasattr(em, "value") else str(em)
        dt = record.detected_document_type
        return cls(
            document_id=record.document_id,
            source_filename=record.source_filename,
            original_file_type=oft_s,
            chunk_id=record.chunk_id,
            page_start=record.page_start,
            page_end=record.page_end,
            section_title=record.section_title,
            document_type=dt.value if hasattr(dt, "value") else str(dt),
            extraction_method=em_s,
            extraction_confidence=record.extraction_confidence,
            extraction_mode="native",
            ocr_used=False,
            ocr_confidence=None,
            percent_empty_pages=0.0,
            section_detection_confidence=None,
            chunk_quality_score=0.0,
            low_quality_chunk=False,
            document_needs_review=False,
            chunk_text=_strip_nul(record.chunk_text),
            processing_timestamp=record.processing_timestamp,
        )


def ingestion_records_from_export_rows(
    rows: list[ExportRow],
    *,
    semantic_document_type: str | None = None,
    processing_timestamp: datetime | None = None,
) -> list[VantageIngestionRecord]:
    """
    Convert pipeline rows to ingestion records.

    ``semantic_document_type`` defaults to ``unknown`` when omitted.
    """
    from vantage_preprocess.models.vantage_domain import DetectedDocumentKind

    sem = semantic_document_type or DetectedDocumentKind.UNKNOWN.value
    ts = processing_timestamp or datetime.now(UTC)
    return [
        VantageIngestionRecord.from_export_row(
            r,
            semantic_document_type=sem,
            processing_timestamp=ts,
        )
        for r in rows
    ]
