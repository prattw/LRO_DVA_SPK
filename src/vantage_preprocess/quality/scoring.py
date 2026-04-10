"""
Lightweight heuristics for extraction reliability and chunk usability.

**Design:** Pure functions over :class:`~vantage_preprocess.models.document.StructuredDocument`
and :class:`~vantage_preprocess.models.document.ExportRow` rows so scores can be recomputed or
replaced with model-based scores later without changing the export schema shape.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from vantage_preprocess.models.document import ExportRow, StructuredDocument
from vantage_preprocess.models.enums import ExtractMethod

logger = logging.getLogger(__name__)

# Pages with fewer non-whitespace characters than this count as "empty" for metrics.
_EMPTY_PAGE_CHAR_THRESHOLD = 40
_LOW_CHUNK_SCORE = 0.45
_REVIEW_DOC_CONFIDENCE = 0.72
_REVIEW_EMPTY_PAGES_PCT = 18.0
_REVIEW_SECTION_CONF = 0.42


def extraction_mode_label(method: ExtractMethod) -> str:
    """Human-facing extraction channel: ``native`` | ``ocr`` | ``hybrid``."""
    if method == ExtractMethod.PARSE:
        return "native"
    if method == ExtractMethod.OCR:
        return "ocr"
    return "hybrid"


def ocr_used(method: ExtractMethod) -> bool:
    return method in (ExtractMethod.OCR, ExtractMethod.HYBRID)


def percent_empty_pages(doc: StructuredDocument, *, min_chars: int = _EMPTY_PAGE_CHAR_THRESHOLD) -> float:
    """Share of pages with very little text (0–100)."""
    if not doc.pages:
        return 0.0
    empty = sum(1 for p in doc.pages if len(p.text.strip()) < min_chars)
    return round(100.0 * empty / len(doc.pages), 2)


def mean_confidence_ocr_pages_in_span(
    doc: StructuredDocument,
    page_start: int,
    page_end: int,
) -> float | None:
    """Mean ``PageText.confidence`` for pages in the span that are not parse-only."""
    rel = [
        p
        for p in doc.pages
        if page_start <= p.page_number <= page_end and p.method != ExtractMethod.PARSE
    ]
    if not rel:
        return None
    return round(sum(p.confidence for p in rel) / len(rel), 4)


@dataclass
class DocumentQualityContext:
    """Document-level metrics (reused for every chunk row from the same document)."""

    document_id: str
    percent_empty_pages: float
    extraction_mode: str
    ocr_used: bool
    document_needs_review: bool
    reasons: list[str] = field(default_factory=list)


def build_document_quality_context(doc: StructuredDocument) -> DocumentQualityContext:
    """Derive document-level flags once per structured document."""
    pct_empty = percent_empty_pages(doc)
    mode = extraction_mode_label(doc.overall_extract_method)
    ocr = ocr_used(doc.overall_extract_method)
    reasons: list[str] = []
    needs = False
    if doc.overall_confidence < _REVIEW_DOC_CONFIDENCE:
        needs = True
        reasons.append(f"overall_confidence<{_REVIEW_DOC_CONFIDENCE}")
    if pct_empty >= _REVIEW_EMPTY_PAGES_PCT:
        needs = True
        reasons.append(f"empty_pages_percent>={_REVIEW_EMPTY_PAGES_PCT}")
    if ocr and doc.overall_confidence < 0.65:
        needs = True
        reasons.append("ocr_overall_confidence_low")

    ctx = DocumentQualityContext(
        document_id=doc.document_id,
        percent_empty_pages=pct_empty,
        extraction_mode=mode,
        ocr_used=ocr,
        document_needs_review=needs,
        reasons=reasons,
    )
    if needs:
        logger.warning(
            "Document quality review suggested: id=%s file=%s reasons=%s",
            doc.document_id[:16],
            doc.source_filename,
            reasons,
        )
    return ctx


def _chunk_quality_score(
    *,
    doc_confidence: float,
    section_confidence: float | None,
    chunk_words: int,
    min_words_hint: int,
) -> float:
    """Scale 0–1 from extraction + section signals + size adequacy."""
    s = float(doc_confidence)
    if section_confidence is not None:
        # Blend section detector confidence (down-weight uncertain sections)
        s *= 0.65 + 0.35 * max(0.0, min(1.0, section_confidence))
    else:
        s *= 0.9
    if chunk_words < min_words_hint:
        s *= 0.88
    return round(max(0.0, min(1.0, s)), 4)


def apply_quality_to_export_rows(
    doc: StructuredDocument,
    rows: list[ExportRow],
    *,
    section_confidence_by_chunk_index: list[float | None],
    min_words_hint: int = 500,
) -> list[ExportRow]:
    """
    Fill quality fields on export rows (same order as ``rows`` / chunk indices).

    ``section_confidence_by_chunk_index`` must align with ``rows`` (post-overlap order).
    """
    ctx = build_document_quality_context(doc)
    out: list[ExportRow] = []
    for i, row in enumerate(rows):
        sec_conf = (
            section_confidence_by_chunk_index[i]
            if i < len(section_confidence_by_chunk_index)
            else None
        )
        p0, p1 = row.page_start, row.page_end
        ocr_conf = mean_confidence_ocr_pages_in_span(doc, p0, p1) if ctx.ocr_used else None

        score = _chunk_quality_score(
            doc_confidence=doc.overall_confidence,
            section_confidence=sec_conf,
            chunk_words=row.chunk_word_count,
            min_words_hint=min_words_hint,
        )
        low = score < _LOW_CHUNK_SCORE or (
            sec_conf is not None and sec_conf < _REVIEW_SECTION_CONF
        )
        if low:
            logger.info(
                "Low-quality chunk flagged: chunk_id=%s score=%s section_conf=%s",
                row.chunk_id,
                score,
                sec_conf,
            )

        out.append(
            row.model_copy(
                update={
                    "extraction_mode": ctx.extraction_mode,
                    "ocr_used": ctx.ocr_used,
                    "ocr_confidence": ocr_conf,
                    "percent_empty_pages": ctx.percent_empty_pages,
                    "section_detection_confidence": sec_conf,
                    "chunk_quality_score": score,
                    "low_quality_chunk": low,
                    "document_needs_review": ctx.document_needs_review,
                },
            ),
        )
    return out


def summarize_job_quality(rows: list[ExportRow]) -> dict[str, object]:
    """Aggregate stats for API ``quality_summary`` / job reports."""
    if not rows:
        return {
            "chunks_total": 0,
            "low_quality_chunks": 0,
            "documents_needing_review": 0,
            "mean_chunk_quality_score": None,
        }
    low = sum(1 for r in rows if r.low_quality_chunk)
    doc_ids = {r.document_id for r in rows if r.document_needs_review}
    scores = [r.chunk_quality_score for r in rows]
    mean_score = round(sum(scores) / len(scores), 4) if scores else None
    return {
        "chunks_total": len(rows),
        "low_quality_chunks": low,
        "documents_needing_review": len(doc_ids),
        "mean_chunk_quality_score": mean_score,
        "fraction_low_quality": round(low / len(rows), 4) if rows else 0.0,
    }
