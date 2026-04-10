"""PDF extraction (native + OCR fallback)."""

from __future__ import annotations

from vantage_preprocess.extract.engine import extract_pdf_document


def extract_pdf(
    content: bytes,
    source_filename: str,
    source_path: str,
    min_text_chars: int = 40,
):
    """Backward-compatible name; ``min_text_chars`` maps to native sparsity threshold."""
    return extract_pdf_document(
        content,
        source_filename,
        source_path,
        min_native_chars=min_text_chars,
    )


__all__ = ["extract_pdf"]
