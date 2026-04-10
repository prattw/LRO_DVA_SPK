"""
Native PDF text extraction only (no OCR).

Use :func:`analyze_native_pages` to get per-page text and ``needs_ocr`` flags, then call OCR
logic separately for flagged pages.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import fitz  # PyMuPDF

from vantage_preprocess.extract.schemas import PdfNativePage
from vantage_preprocess.utils.text import normalize_whitespace

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def count_non_whitespace_chars(text: str) -> int:
    """Count characters excluding whitespace (unit-testable sparsity signal)."""
    return len(re.sub(r"\s+", "", text, flags=re.UNICODE))


def page_needs_ocr(
    non_whitespace_char_count: int,
    *,
    min_chars: int,
) -> bool:
    """Return True if native text is too sparse to trust without OCR."""
    return non_whitespace_char_count < min_chars


def analyze_pdf_page_native(
    page: fitz.Page,
    page_number: int,
    *,
    min_chars: int,
) -> PdfNativePage:
    """
    Extract text with PyMuPDF only and classify sparsity.

    Does not rasterize or call Tesseract.
    """
    raw = page.get_text("text") or ""
    stripped = raw.strip()
    normalized = normalize_whitespace(stripped) if stripped else ""
    n = count_non_whitespace_chars(normalized)
    needs = page_needs_ocr(n, min_chars=min_chars)
    if needs:
        logger.debug(
            "PDF page %s native text sparse: %s non-whitespace chars (min %s)",
            page_number,
            n,
            min_chars,
        )
    return PdfNativePage(
        page_number=page_number,
        text=normalized,
        non_whitespace_char_count=n,
        needs_ocr=needs,
    )


def analyze_native_pages(
    pdf_bytes: bytes,
    *,
    min_chars: int,
) -> list[PdfNativePage]:
    """
    Run native extraction for every page of a PDF document.

    Raises:
        RuntimeError: if the PDF cannot be opened.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    out: list[PdfNativePage] = []
    try:
        for i in range(doc.page_count):
            page = doc.load_page(i)
            out.append(
                analyze_pdf_page_native(
                    page,
                    i + 1,
                    min_chars=min_chars,
                ),
            )
    finally:
        doc.close()
    return out
