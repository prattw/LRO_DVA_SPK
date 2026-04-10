"""Heuristic extraction/chunk quality scoring."""

from __future__ import annotations

from vantage_preprocess.models.document import ExportRow, PageText, StructuredDocument
from vantage_preprocess.models.enums import DocumentType, ExtractMethod
from vantage_preprocess.quality.scoring import (
    apply_quality_to_export_rows,
    build_document_quality_context,
    percent_empty_pages,
    summarize_job_quality,
)


def _doc_two_pages() -> StructuredDocument:
    return StructuredDocument(
        document_id="a" * 32,
        source_filename="t.pdf",
        source_path="/x",
        source_sha256="b" * 64,
        mime_type="application/pdf",
        document_type=DocumentType.PDF,
        pages=[
            PageText(page_number=1, text="x" * 50, method=ExtractMethod.PARSE, confidence=1.0),
            PageText(page_number=2, text="", method=ExtractMethod.PARSE, confidence=1.0),
        ],
        overall_extract_method=ExtractMethod.PARSE,
        overall_confidence=0.95,
        docx_extraction=None,
    )


def test_percent_empty_pages() -> None:
    doc = _doc_two_pages()
    assert percent_empty_pages(doc) == 50.0


def test_document_quality_context_flags_sparse() -> None:
    doc = _doc_two_pages()
    ctx = build_document_quality_context(doc)
    assert ctx.extraction_mode == "native"
    assert ctx.ocr_used is False
    assert ctx.percent_empty_pages == 50.0


def test_apply_quality_sets_scores_and_flags() -> None:
    doc = _doc_two_pages()
    rows = [
        ExportRow(
            document_id=doc.document_id,
            source_filename=doc.source_filename,
            page_start=1,
            page_end=2,
            section_title=None,
            chunk_id=f"{doc.document_id}-chunk-0001",
            chunk_text="hello " * 200,
            document_type=doc.document_type,
            confidence=doc.overall_confidence,
            extracted_method=doc.overall_extract_method,
            chunk_word_count=200,
            chunk_index=1,
            total_chunks=1,
        ),
    ]
    out = apply_quality_to_export_rows(
        doc,
        rows,
        section_confidence_by_chunk_index=[0.9],
        min_words_hint=500,
    )
    assert out[0].chunk_quality_score > 0.0
    assert out[0].percent_empty_pages == 50.0
    assert out[0].extraction_mode == "native"
    assert out[0].ocr_used is False
    summ = summarize_job_quality(out)
    assert summ["chunks_total"] == 1
    assert "mean_chunk_quality_score" in summ
