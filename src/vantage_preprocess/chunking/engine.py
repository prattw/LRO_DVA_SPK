"""
Chunking engine: section-aware primary path, paragraph fallback, overlap, validation, export rows.

**Why these sizes:** 500–2,000 words (~375–1,500 tokens at 0.75 w/token) matches common embedding
model context windows and keeps each chunk semantically dense enough for retrieval while avoiding
under-sized fragments that lack context. The 1,200–1,500 word target balances recall (enough
signal per vector) against precision (limits mixed topics). Overlap reduces boundary effects when
answers span chunk edges, improving downstream QA and RAG recall.

**Query/retrieval:** Stable ``chunk_id`` values, page spans, and ``section_title`` support
filtering, page citations, and joining back to the parent via ``document_id`` and ``source_sha256``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from vantage_preprocess.chunking.config import ChunkingConfig
from vantage_preprocess.chunking.overlap import apply_overlap_safe
from vantage_preprocess.chunking.strategies import ParagraphChunker, RawChunk, SectionAwareChunker
from vantage_preprocess.chunking.validate import ChunkValidationReport, validate_chunks
from vantage_preprocess.chunking.words import count_words
from vantage_preprocess.models.document import ExportRow, StructuredDocument
from vantage_preprocess.quality.scoring import apply_quality_to_export_rows
from vantage_preprocess.utils.ids import format_vantage_chunk_id
from vantage_preprocess.utils.text import normalize_whitespace

logger = logging.getLogger(__name__)


@dataclass
class ChunkingRunResult:
    """Chunking output plus diagnostics."""

    rows: list[ExportRow]
    strategy_used: str
    validation: ChunkValidationReport
    notes: list[str] = field(default_factory=list)


def build_export_rows(
    doc: StructuredDocument,
    config: ChunkingConfig | None = None,
) -> list[ExportRow]:
    """Run chunking; return :class:`~vantage_preprocess.models.document.ExportRow` list."""
    return chunk_document(doc, config).rows


def chunk_document(
    doc: StructuredDocument,
    config: ChunkingConfig | None = None,
) -> ChunkingRunResult:
    """Full chunking pipeline with validation metadata."""
    cfg = config or ChunkingConfig()
    notes: list[str] = []

    raw_chunks = SectionAwareChunker(cfg).build_raw_chunks(doc)
    strategy = "section_aware"
    if not raw_chunks:
        raw_chunks = ParagraphChunker(cfg).build_raw_chunks(doc)
        strategy = "paragraph_fallback"
        notes.append("Section-aware chunking produced no segments; used paragraph fallback.")

    if not raw_chunks:
        full = normalize_whitespace("\n\n".join(p.text for p in doc.pages))
        if full:
            raw_chunks = [
                RawChunk(
                    section_title=None,
                    text=full,
                    page_start=doc.pages[0].page_number,
                    page_end=doc.pages[-1].page_number,
                    section_detection_confidence=None,
                ),
            ]
            strategy = "paragraph_fallback"
            notes.append("No sections or paragraphs; emitted whole document as one segment.")
        else:
            notes.append("Document has no extractable text; no rows produced.")
            return ChunkingRunResult(
                rows=[],
                strategy_used=strategy,
                validation=ChunkValidationReport(),
                notes=notes,
            )

    segments = [r.text for r in raw_chunks]
    overlapped = apply_overlap_safe(segments, cfg.overlap_target(), cfg.max_words)
    val = validate_chunks(overlapped, cfg)
    if val.errors:
        logger.error("Chunk validation failed: %s", val.errors)

    n = len(overlapped)
    rows: list[ExportRow] = []
    section_conf_by_index: list[float | None] = []
    for i, text in enumerate(overlapped):
        rc = raw_chunks[i]
        wc = count_words(text)
        section_conf_by_index.append(rc.section_detection_confidence)
        rows.append(
            ExportRow(
                document_id=doc.document_id,
                source_filename=doc.source_filename,
                page_start=rc.page_start,
                page_end=rc.page_end,
                section_title=rc.section_title,
                chunk_id=format_vantage_chunk_id(doc.document_id, i + 1),
                chunk_text=text,
                document_type=doc.document_type,
                confidence=doc.overall_confidence,
                extracted_method=doc.overall_extract_method,
                mime_type=doc.mime_type,
                source_sha256=doc.source_sha256,
                chunk_word_count=wc,
                chunk_index=i + 1,
                total_chunks=n,
            ),
        )

    rows = apply_quality_to_export_rows(
        doc,
        rows,
        section_confidence_by_chunk_index=section_conf_by_index,
        min_words_hint=cfg.min_words,
    )

    return ChunkingRunResult(
        rows=rows,
        strategy_used=strategy,
        validation=val,
        notes=notes,
    )
