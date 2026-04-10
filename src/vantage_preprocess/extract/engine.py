"""
High-level extraction API producing :class:`~vantage_preprocess.models.document.StructuredDocument`.

Compose native PDF analysis, optional OCR fallback, DOCX, TXT, CSV, and Excel.
"""

from __future__ import annotations

import logging

from vantage_preprocess.extract.docx_extract import extract_docx_blocks
from vantage_preprocess.extract.pdf_native import analyze_native_pages
from vantage_preprocess.extract.pdf_ocr_fallback import apply_ocr_for_flagged_pages
from vantage_preprocess.extract.tabular import extract_csv_to_text, extract_xlsx_to_text
from vantage_preprocess.models.document import PageText, StructuredDocument
from vantage_preprocess.models.enums import DocumentType, ExtractMethod
from vantage_preprocess.models.vantage_domain import ExtractedPage
from vantage_preprocess.utils.ids import document_id_from_bytes, file_sha256
from vantage_preprocess.utils.text import normalize_whitespace

logger = logging.getLogger(__name__)

_DEFAULT_MIN_CHARS = 40


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _combine_methods(methods: list[ExtractMethod]) -> ExtractMethod:
    unique = set(methods)
    if not unique:
        return ExtractMethod.PARSE
    if len(unique) == 1:
        return next(iter(unique))
    if unique <= {ExtractMethod.PARSE, ExtractMethod.HYBRID}:
        return ExtractMethod.HYBRID if ExtractMethod.HYBRID in unique else ExtractMethod.PARSE
    if ExtractMethod.OCR in unique or ExtractMethod.HYBRID in unique:
        return ExtractMethod.HYBRID
    return ExtractMethod.OCR


def extract_pdf_document(
    content: bytes,
    source_filename: str,
    source_path: str,
    *,
    min_native_chars: int = _DEFAULT_MIN_CHARS,
) -> StructuredDocument:
    """
    PDF: native text per page, sparse pages flagged, then OCR fallback where needed.

    Replaces the legacy single-module PDF extractor; see ``extract.pdf.extract_pdf``.
    """
    did = document_id_from_bytes(content, source_filename)
    sha = file_sha256(content)

    native = analyze_native_pages(content, min_chars=min_native_chars)
    flagged = sum(1 for p in native if p.needs_ocr)
    logger.info(
        "PDF %s: %s pages, %s flagged for OCR",
        source_filename,
        len(native),
        flagged,
    )

    tuples = apply_ocr_for_flagged_pages(content, native)
    pages: list[PageText] = []
    methods: list[ExtractMethod] = []
    confs: list[float] = []
    for pnum, text, method, conf in tuples:
        pages.append(
            PageText(
                page_number=pnum,
                text=text,
                method=method,
                confidence=conf,
            ),
        )
        methods.append(method)
        confs.append(conf)

    return StructuredDocument(
        document_id=did,
        source_filename=source_filename,
        source_path=source_path,
        source_sha256=sha,
        mime_type="application/pdf",
        document_type=DocumentType.PDF,
        pages=pages,
        overall_extract_method=_combine_methods(methods),
        overall_confidence=_mean(confs),
    )


def extract_docx_document(
    content: bytes,
    source_filename: str,
    source_path: str,
) -> StructuredDocument:
    """DOCX: ordered headings + paragraphs flattened to one logical page."""
    did = document_id_from_bytes(content, source_filename)
    sha = file_sha256(content)
    result = extract_docx_blocks(content)
    text = normalize_whitespace(result.flattened_text())
    page = PageText(
        page_number=1,
        text=text,
        method=ExtractMethod.PARSE,
        confidence=1.0,
    )
    return StructuredDocument(
        document_id=did,
        source_filename=source_filename,
        source_path=source_path,
        source_sha256=sha,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        document_type=DocumentType.DOCX,
        pages=[page],
        overall_extract_method=ExtractMethod.PARSE,
        overall_confidence=1.0,
        docx_extraction=result,
    )


def structured_document_to_extracted_pages(doc: StructuredDocument) -> list[ExtractedPage]:
    """
    Map pipeline :class:`StructuredDocument` to canonical :class:`ExtractedPage` rows.

    Use for Army Vantage–style provenance and API responses.
    """
    return [
        ExtractedPage(
            document_id=doc.document_id,
            page_number=pt.page_number,
            text=pt.text,
            extraction_method=pt.method,
            extraction_confidence=pt.confidence,
            parent_document_hash=doc.source_sha256,
        )
        for pt in doc.pages
    ]


def extract_txt_document(
    content: bytes,
    source_filename: str,
    source_path: str,
) -> StructuredDocument:
    """Plain text as a single page."""
    did = document_id_from_bytes(content, source_filename)
    sha = file_sha256(content)
    text = content.decode("utf-8", errors="replace")
    text = normalize_whitespace(text)
    page = PageText(
        page_number=1,
        text=text,
        method=ExtractMethod.PARSE,
        confidence=1.0,
    )
    return StructuredDocument(
        document_id=did,
        source_filename=source_filename,
        source_path=source_path,
        source_sha256=sha,
        mime_type="text/plain",
        document_type=DocumentType.TXT,
        pages=[page],
        overall_extract_method=ExtractMethod.PARSE,
        overall_confidence=1.0,
    )


def extract_csv_document(
    content: bytes,
    source_filename: str,
    source_path: str,
) -> StructuredDocument:
    """CSV/TSV flattened to tab-separated lines (one logical page)."""
    did = document_id_from_bytes(content, source_filename)
    sha = file_sha256(content)
    raw = extract_csv_to_text(content)
    text = normalize_whitespace(raw)
    logger.info("CSV %s: extracted text length %s", source_filename, len(text))
    page = PageText(
        page_number=1,
        text=text,
        method=ExtractMethod.PARSE,
        confidence=1.0,
    )
    return StructuredDocument(
        document_id=did,
        source_filename=source_filename,
        source_path=source_path,
        source_sha256=sha,
        mime_type="text/csv",
        document_type=DocumentType.CSV,
        pages=[page],
        overall_extract_method=ExtractMethod.PARSE,
        overall_confidence=1.0,
    )


def extract_xlsx_document(
    content: bytes,
    source_filename: str,
    source_path: str,
) -> StructuredDocument:
    """Excel workbook (xlsx/xlsm): all sheets as labeled sections, one logical page."""
    did = document_id_from_bytes(content, source_filename)
    sha = file_sha256(content)
    raw = extract_xlsx_to_text(content)
    text = normalize_whitespace(raw)
    logger.info("Excel %s: extracted text length %s", source_filename, len(text))
    page = PageText(
        page_number=1,
        text=text,
        method=ExtractMethod.PARSE,
        confidence=1.0,
    )
    return StructuredDocument(
        document_id=did,
        source_filename=source_filename,
        source_path=source_path,
        source_sha256=sha,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        document_type=DocumentType.XLSX,
        pages=[page],
        overall_extract_method=ExtractMethod.PARSE,
        overall_confidence=1.0,
    )
