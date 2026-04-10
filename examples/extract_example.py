#!/usr/bin/env python3
"""
Example: run modular extraction on files or in-memory bytes.

Usage (from repo root, with venv activated)::

    python examples/extract_example.py /path/to/file.pdf
    python examples/extract_example.py sample.docx
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from vantage_preprocess.extract.engine import (
    extract_csv_document,
    extract_docx_document,
    extract_pdf_document,
    extract_txt_document,
    extract_xlsx_document,
    structured_document_to_extracted_pages,
)
from vantage_preprocess.extract.pdf_native import analyze_native_pages

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.is_file():
        logger.error("Not a file: %s", path)
        sys.exit(1)

    data = path.read_bytes()
    name = path.name
    spath = str(path.resolve())

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        native = analyze_native_pages(data, min_chars=40)
        flags = [p.needs_ocr for p in native]
        logger.info("Native PDF: %s pages, OCR flags: %s", len(native), flags)
        doc = extract_pdf_document(data, name, spath)
    elif suffix == ".docx":
        doc = extract_docx_document(data, name, spath)
    elif suffix in (".txt", ".md"):
        doc = extract_txt_document(data, name, spath)
    elif suffix in (".csv", ".tsv"):
        doc = extract_csv_document(data, name, spath)
    elif suffix in (".xlsx", ".xlsm"):
        doc = extract_xlsx_document(data, name, spath)
    else:
        logger.error("Unsupported extension: %s", suffix)
        sys.exit(1)

    pages = structured_document_to_extracted_pages(doc)
    logger.info(
        "StructuredDocument pages=%s overall=%s",
        len(doc.pages),
        doc.overall_extract_method,
    )
    for ep in pages[:5]:
        preview = (ep.text[:120] + "…") if len(ep.text) > 120 else ep.text
        one_line = preview.replace("\n", " ")
        logger.info("  p%s [%s] %s", ep.page_number, ep.extraction_method, one_line)


if __name__ == "__main__":
    main()
