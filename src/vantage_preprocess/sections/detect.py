"""Orchestrate DOCX-style headings vs PDF/TXT heuristics."""

from __future__ import annotations

from vantage_preprocess.extract.schemas import DocxBlockKind
from vantage_preprocess.models.document import StructuredDocument
from vantage_preprocess.models.enums import DocumentType
from vantage_preprocess.sections.docx_sections import sections_from_docx_blocks
from vantage_preprocess.sections.models import SectionDetectionResult
from vantage_preprocess.sections.text_heuristic import sections_from_page_text_heuristic


def detect_sections(doc: StructuredDocument) -> SectionDetectionResult:
    """
    Prefer Word heading styles when ``docx_extraction`` is present and contains heading blocks;
    otherwise use construction text patterns on ``doc.pages`` (PDF, TXT, or unstyled DOCX).
    """
    if doc.document_type == DocumentType.DOCX and doc.docx_extraction is not None:
        blocks = doc.docx_extraction.blocks
        has_heading = any(b.kind == DocxBlockKind.HEADING for b in blocks)
        if has_heading:
            sections, notes = sections_from_docx_blocks(doc.docx_extraction)
            return SectionDetectionResult(
                sections=sections,
                strategy="docx_styles",
                notes=notes,
            )
        secs, strat, n2 = sections_from_page_text_heuristic(doc.pages)
        merged = [
            "DOCX had no styled headings; fell back to line-pattern detection on flattened text.",
        ] + n2
        return SectionDetectionResult(sections=secs, strategy=strat, notes=merged)

    secs, strat, notes = sections_from_page_text_heuristic(doc.pages)
    return SectionDetectionResult(sections=secs, strategy=strat, notes=notes)
