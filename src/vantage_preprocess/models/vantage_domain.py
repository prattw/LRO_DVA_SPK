"""
Canonical domain models for Army Vantage document preprocessing and ingestion.

**Why these shapes:** Vantage ingests structured rows (often CSV/JSONL) where each record must
tie text back to a stable document identity, page range, and provenance. These models encode
that contract explicitly so exports are auditable (hash + timestamp + method) and safe for
retrieval (chunk boundaries + section context).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from vantage_preprocess.models.document import SCHEMA_VERSION as LEGACY_SCHEMA_VERSION
from vantage_preprocess.models.document import ExportRow
from vantage_preprocess.models.enums import DocumentType, ExtractMethod

VANTAGE_EXPORT_SCHEMA_VERSION = "2"


class DetectedDocumentKind(StrEnum):
    """
    High-level *semantic* classification for retrieval filters in Vantage.

    Distinct from :class:`DocumentType` (file format): e.g. a PDF can be ``pdf`` but
    ``specification_section`` for detected content.
    """

    UNKNOWN = "unknown"
    SPECIFICATION_SECTION = "specification_section"
    SUBMITTAL_PACKAGE = "submittal_package"
    DRAWING_SHEET = "drawing_sheet"
    CORRESPONDENCE = "correspondence"
    FORM_TABLE = "form_table"
    OTHER = "other"


def _sha256_hex(v: Any) -> str:
    if not isinstance(v, str):
        raise TypeError("expected string")
    s = v.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", s):
        raise ValueError("must be a 64-character lowercase hexadecimal SHA-256 digest")
    return s


Sha256Hex = Annotated[str, Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")]


class UploadedDocument(BaseModel):
    """
    Metadata for a file after intake (before or after text extraction).

    **Vantage ingestion:** Gives a stable ``document_id`` and ``parent_document_hash`` so every
    downstream chunk/export row can reference the same source blob, even if the file is renamed
    in storage.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str = Field(
        min_length=8,
        description="Stable identifier (e.g. hash of bytes + filename salt).",
    )
    source_filename: str = Field(
        min_length=1,
        max_length=1024,
        description="Original basename as uploaded.",
    )
    original_file_type: DocumentType = Field(
        description="Format classification from extension/MIME (pdf, docx, …).",
    )
    byte_size: int = Field(ge=0, description="Size in bytes after intake validation.")
    parent_document_hash: Sha256Hex = Field(
        description="SHA-256 of file bytes; integrity anchor for CUI/audit trails.",
    )
    mime_type: str | None = Field(
        default=None,
        max_length=256,
        description="MIME type if known (optional).",
    )
    storage_uri: str | None = Field(
        default=None,
        description="Optional path or object key where the blob is stored (CLI: local path).",
    )
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When intake completed (UTC).",
    )

    @field_validator("parent_document_hash", mode="before")
    @classmethod
    def normalize_sha256(cls, v: Any) -> str:
        return _sha256_hex(v)


class ExtractedPage(BaseModel):
    """
    Text and quality signals for one page (1-based index).

    **Vantage ingestion:** Page anchors let Vantage cite “which page” in UI/snippets; confidence
    supports filtering low-quality OCR before retrieval.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str = Field(min_length=8)
    page_number: int = Field(ge=1, description="1-based page index within the source document.")
    text: str = Field(description="Normalized page text (may be empty if unreadable).")
    extraction_method: ExtractMethod = Field(
        description="parse = native text; ocr = Tesseract; hybrid = both merged.",
    )
    extraction_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Mean OCR confidence or 1.0 for pure parse when not applicable.",
    )
    parent_document_hash: Sha256Hex = Field(
        description="Same as uploaded file hash for traceability.",
    )

    @field_validator("parent_document_hash", mode="before")
    @classmethod
    def normalize_sha256(cls, v: Any) -> str:
        return _sha256_hex(v)


class DetectedSection(BaseModel):
    """
    A heading-bounded region spanning one or more pages.

    **Vantage ingestion:** ``section_title`` becomes a facet for chunk grouping and UI
    breadcrumbs; page span prevents cross-document bleed in retrieval.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str = Field(min_length=8)
    section_title: str | None = Field(
        default=None,
        max_length=2000,
        description="Detected heading text, if any.",
    )
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    body_text: str = Field(
        default="",
        description="Full section body (may be chunked later without losing section identity).",
    )
    parent_document_hash: Sha256Hex = Field(description="Anchors section to source blob.")

    @field_validator("parent_document_hash", mode="before")
    @classmethod
    def normalize_sha256(cls, v: Any) -> str:
        return _sha256_hex(v)

    @model_validator(mode="after")
    def page_order(self) -> Self:
        if self.page_end < self.page_start:
            raise ValueError("page_end must be >= page_start")
        return self


class ExportRecord(BaseModel):
    """
    One row in a Vantage-ingestible dataset (JSONL/CSV/XLSX).

    **Vantage ingestion:** Maps cleanly to tabular import: each row is self-contained for
    retrieval (text + ids + provenance). Use ``schema_version`` to migrate fields over time.
    """

    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    schema_version: str = Field(
        default=VANTAGE_EXPORT_SCHEMA_VERSION,
        min_length=1,
        description="Bump when columns change for downstream ETL.",
    )
    document_id: str = Field(min_length=8)
    source_filename: str = Field(min_length=1, max_length=1024)
    original_file_type: DocumentType = Field(
        description="File format of the source upload (pdf, docx, …).",
    )
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section_title: str | None = Field(default=None, max_length=2000)
    chunk_id: str = Field(min_length=4)
    chunk_text: str = Field(description="Primary text for embedding and display.")
    extraction_method: ExtractMethod
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    detected_document_type: DetectedDocumentKind = Field(
        default=DetectedDocumentKind.UNKNOWN,
        description="Semantic classification for Vantage filters and relevance tuning.",
    )
    parent_document_hash: Sha256Hex = Field(
        description="SHA-256 of original bytes; join key to UploadedDocument.",
    )
    processing_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC time when this record was finalized.",
    )

    @field_validator("parent_document_hash", mode="before")
    @classmethod
    def normalize_sha256(cls, v: Any) -> str:
        return _sha256_hex(v)

    @model_validator(mode="after")
    def pages(self) -> Self:
        if self.page_end < self.page_start:
            raise ValueError("page_end must be >= page_start")
        return self

    def to_legacy_export_row(self) -> ExportRow:
        """
        Map to the existing pipeline :class:`ExportRow` for current writers (schema v1).

        Loses ``detected_document_type`` and ``processing_timestamp`` in the legacy shape unless
        you extend :class:`ExportRow` later.
        """
        return ExportRow(
            schema_version=LEGACY_SCHEMA_VERSION,
            document_id=self.document_id,
            source_filename=self.source_filename,
            page_start=self.page_start,
            page_end=self.page_end,
            section_title=self.section_title,
            chunk_id=self.chunk_id,
            chunk_text=self.chunk_text,
            document_type=self.original_file_type,
            confidence=self.extraction_confidence,
            extracted_method=self.extraction_method,
            mime_type=None,
            source_sha256=self.parent_document_hash,
        )

    @classmethod
    def from_legacy_export_row(cls, row: ExportRow) -> Self:
        """Best-effort upgrade from v1 :class:`ExportRow` (semantic type unknown)."""
        if not row.source_sha256:
            raise ValueError("legacy ExportRow requires source_sha256 for parent_document_hash")
        return cls(
            document_id=row.document_id,
            source_filename=row.source_filename,
            original_file_type=row.document_type,
            page_start=row.page_start,
            page_end=row.page_end,
            section_title=row.section_title,
            chunk_id=row.chunk_id,
            chunk_text=row.chunk_text,
            extraction_method=row.extracted_method,
            extraction_confidence=row.confidence,
            detected_document_type=DetectedDocumentKind.UNKNOWN,
            parent_document_hash=row.source_sha256,
            processing_timestamp=datetime.now(UTC),
        )


class DocumentChunk(BaseModel):
    """
    A logical chunk after sectioning and before final serialization to export.

    **Vantage ingestion:** This is the natural unit for embedding + retrieval; fields mirror what
    you will flatten into :class:`ExportRecord`.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str = Field(min_length=8)
    source_filename: str = Field(min_length=1, max_length=1024)
    original_file_type: DocumentType
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section_title: str | None = Field(default=None, max_length=2000)
    chunk_id: str = Field(
        min_length=4,
        description="Unique within corpus run (e.g. doc prefix + seq).",
    )
    chunk_text: str = Field(description="Text payload for Vantage.")
    extraction_method: ExtractMethod
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    detected_document_type: DetectedDocumentKind = Field(
        default=DetectedDocumentKind.UNKNOWN,
        description="Semantic type guess for filtering/boosting in Vantage.",
    )
    parent_document_hash: Sha256Hex
    processing_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this chunk was produced (UTC).",
    )

    @field_validator("parent_document_hash", mode="before")
    @classmethod
    def normalize_sha256(cls, v: Any) -> str:
        return _sha256_hex(v)

    @model_validator(mode="after")
    def pages(self) -> Self:
        if self.page_end < self.page_start:
            raise ValueError("page_end must be >= page_start")
        return self

    def to_export_record(self) -> ExportRecord:
        """Flatten to a row ready for JSONL/CSV/XLSX."""
        return ExportRecord(
            schema_version=VANTAGE_EXPORT_SCHEMA_VERSION,
            document_id=self.document_id,
            source_filename=self.source_filename,
            original_file_type=self.original_file_type,
            page_start=self.page_start,
            page_end=self.page_end,
            section_title=self.section_title,
            chunk_id=self.chunk_id,
            chunk_text=self.chunk_text,
            extraction_method=self.extraction_method,
            extraction_confidence=self.extraction_confidence,
            detected_document_type=self.detected_document_type,
            parent_document_hash=self.parent_document_hash,
            processing_timestamp=self.processing_timestamp,
        )


class ProcessingResult(BaseModel):
    """
    Outcome of processing one upload through the pipeline (or a single step).

    **Vantage ingestion:** Attach as job metadata or sidecar JSON next to exports so operators can
    reconcile failures without opening logs.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str | None = Field(
        default=None,
        description="Set when processing targets a single document.",
    )
    source_filename: str | None = None
    success: bool = Field(
        description="True if extraction + chunking completed without fatal error.",
    )
    message: str = Field(
        default="",
        max_length=8000,
        description="Human-readable status or error summary.",
    )
    chunks_produced: int = Field(ge=0, default=0)
    pages_extracted: int = Field(ge=0, default=0)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    error_code: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def completed_after_start(self) -> Self:
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at must be >= started_at")
        return self
