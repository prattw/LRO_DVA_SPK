from __future__ import annotations

from dataclasses import dataclass, field

from vantage_preprocess.models.document import PageText, StructuredDocument
from vantage_preprocess.models.enums import DocumentType, ExtractMethod
from vantage_preprocess.sections.detect import detect_sections


@dataclass
class SectionBlock:
    """One section slice for chunking (see ``vantage_preprocess.sections`` models)."""

    section_title: str | None
    page_start: int
    page_end: int
    text: str
    heading_source: str | None = None
    heading_confidence: float | None = None
    detection_notes: tuple[str, ...] = field(default_factory=tuple)


def section_blocks_from_document(doc: StructuredDocument) -> list[SectionBlock]:
    """Split document text using DOCX styles when available, else PDF/TXT heuristics."""
    det = detect_sections(doc)
    blocks: list[SectionBlock] = []
    for s in det.sections:
        blocks.append(
            SectionBlock(
                section_title=s.heading_text,
                page_start=s.page_start,
                page_end=s.page_end,
                text=s.body_text,
                heading_source=s.heading_source.value,
                heading_confidence=s.confidence,
                detection_notes=tuple(s.reasons),
            ),
        )
    return blocks


def pages_to_section_blocks(pages: list[PageText]) -> list[SectionBlock]:
    """
    Legacy helper: only page text (no DOCX blocks).

    Prefer :func:`section_blocks_from_document` with a full
    :class:`~vantage_preprocess.models.document.StructuredDocument` so DOCX
    heading styles can be used when present.
    """
    doc = StructuredDocument(
        document_id="0" * 32,
        source_filename="_anonymous",
        source_path="",
        source_sha256="0" * 64,
        mime_type=None,
        document_type=DocumentType.TXT,
        pages=pages,
        overall_extract_method=ExtractMethod.PARSE,
        overall_confidence=1.0,
        docx_extraction=None,
    )
    return section_blocks_from_document(doc)
