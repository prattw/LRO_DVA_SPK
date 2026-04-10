"""Unit tests for PDF native analysis helpers (no OCR required)."""

from __future__ import annotations

import fitz

from vantage_preprocess.extract.pdf_native import (
    analyze_native_pages,
    count_non_whitespace_chars,
    page_needs_ocr,
)


def test_count_non_whitespace_chars() -> None:
    assert count_non_whitespace_chars("a b \n c") == 3
    assert count_non_whitespace_chars("") == 0


def test_page_needs_ocr_threshold() -> None:
    assert page_needs_ocr(0, min_chars=40) is True
    assert page_needs_ocr(39, min_chars=40) is True
    assert page_needs_ocr(40, min_chars=40) is False


def test_analyze_native_pages_text_pdf() -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello world. " * 20)
    pdf_bytes = doc.tobytes()
    doc.close()

    pages = analyze_native_pages(pdf_bytes, min_chars=40)
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].needs_ocr is False
    assert pages[0].non_whitespace_char_count >= 40


def test_analyze_native_pages_sparse_pdf() -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hi")
    pdf_bytes = doc.tobytes()
    doc.close()

    pages = analyze_native_pages(pdf_bytes, min_chars=40)
    assert len(pages) == 1
    assert pages[0].needs_ocr is True
