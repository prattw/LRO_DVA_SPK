from __future__ import annotations

from pydantic import BaseModel, Field

from vantage_preprocess.extract.schemas import DocxExtractionResult
from vantage_preprocess.models.enums import DocumentType, ExtractMethod

SCHEMA_VERSION = "3"


class PageText(BaseModel):
    """Text extracted for a single page (1-based page index)."""

    page_number: int = Field(ge=1)
    text: str
    method: ExtractMethod
    confidence: float = Field(ge=0.0, le=1.0, description="Mean confidence for this page")


class StructuredDocument(BaseModel):
    """Internal representation after extract + light section tagging."""

    document_id: str
    source_filename: str
    source_path: str
    source_sha256: str
    mime_type: str | None
    document_type: DocumentType
    pages: list[PageText]
    overall_extract_method: ExtractMethod
    overall_confidence: float
    docx_extraction: DocxExtractionResult | None = Field(
        default=None,
        description="Ordered DOCX blocks when source is Word (enables heading-style detection).",
    )


class ExportRow(BaseModel):
    """One chunk row suitable for JSONL/CSV/XLSX export."""

    schema_version: str = SCHEMA_VERSION
    document_id: str
    source_filename: str
    page_start: int
    page_end: int
    section_title: str | None
    chunk_id: str
    chunk_text: str
    document_type: DocumentType
    confidence: float
    extracted_method: ExtractMethod
    mime_type: str | None = None
    source_sha256: str | None = None
    chunk_word_count: int = Field(default=0, ge=0, description="Words in chunk_text (approximate).")
    chunk_index: int = Field(default=1, ge=1, description="1-based index within this document.")
    total_chunks: int = Field(
        default=1,
        ge=1,
        description="Total chunks emitted for this document.",
    )
    # Extraction / chunk quality (heuristic; see vantage_preprocess.quality.scoring)
    extraction_mode: str = Field(
        default="native",
        description="native | ocr | hybrid — coarse channel for the document.",
    )
    ocr_used: bool = Field(default=False, description="True when OCR or hybrid extraction ran.")
    ocr_confidence: float | None = Field(
        default=None,
        description="Mean page confidence for OCR/hybrid pages overlapping this chunk span.",
    )
    percent_empty_pages: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Share of pages with very little text (document-level, repeated on rows).",
    )
    section_detection_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence from section/heading detection for this chunk's merged section.",
    )
    chunk_quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Heuristic 0–1 score for chunk usability.",
    )
    low_quality_chunk: bool = Field(
        default=False,
        description="True when score or section confidence suggests manual review.",
    )
    document_needs_review: bool = Field(
        default=False,
        description="Document-level flag (repeated on each chunk row).",
    )
