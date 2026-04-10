"""
OCR fallback for PDF pages flagged after native extraction.

Uses :class:`~vantage_preprocess.ocr.service.OcrService` (pluggable provider + preprocessing).
"""

from __future__ import annotations

import logging

import fitz
from PIL import Image

from vantage_preprocess.extract.schemas import PdfNativePage
from vantage_preprocess.models.enums import ExtractMethod
from vantage_preprocess.ocr import get_default_ocr_service
from vantage_preprocess.ocr.service import OcrService
from vantage_preprocess.utils.text import normalize_whitespace

logger = logging.getLogger(__name__)

# Raster scale for OCR (higher = better for small text, slower)
_DEFAULT_OCR_MATRIX = fitz.Matrix(2.0, 2.0)


def rasterize_page_rgb(page: fitz.Page, matrix: fitz.Matrix | None = None) -> Image.Image:
    """Render a PDF page to a PIL RGB image."""
    mat = matrix or _DEFAULT_OCR_MATRIX
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def ocr_single_pdf_page(
    page: fitz.Page,
    page_number: int,
    *,
    ocr_service: OcrService | None = None,
) -> tuple[str, float, ExtractMethod]:
    """
    Run OCR on a rasterized page via the configured :class:`OcrService`.

    Returns:
        (normalized_text, confidence 0..1, method OCR).
    """
    svc = ocr_service or get_default_ocr_service()
    if not svc.provider.is_available():
        logger.warning(
            "OCR provider %s unavailable; skipped for page %s",
            svc.provider.provider_id,
            page_number,
        )
        return "", 0.0, ExtractMethod.OCR
    img = rasterize_page_rgb(page)
    r = svc.ocr_pil(img, page_number)
    if r.error:
        logger.error(
            "OCR failure page=%s provider=%s: %s",
            page_number,
            r.provider_id,
            r.error,
        )
    text = normalize_whitespace(r.text)
    return text, r.confidence, ExtractMethod.OCR


def merge_native_and_ocr_text(
    native_text: str,
    ocr_text: str,
    ocr_confidence: float,
) -> tuple[str, ExtractMethod, float]:
    """
    Combine sparse native text with OCR output.

    If both non-empty, returns hybrid text and HYBRID with blended confidence.
    """
    n = native_text.strip()
    o = ocr_text.strip()
    if n and o:
        merged = normalize_whitespace(f"{n}\n\n{o}".strip())
        blended = min(1.0, (0.95 + ocr_confidence) / 2)
        return merged, ExtractMethod.HYBRID, blended
    if o:
        return o, ExtractMethod.OCR, ocr_confidence
    if n:
        return n, ExtractMethod.PARSE, 0.35
    return "", ExtractMethod.PARSE, 0.0


def apply_ocr_for_flagged_pages(
    pdf_bytes: bytes,
    native_pages: list[PdfNativePage],
    *,
    ocr_service: OcrService | None = None,
) -> list[tuple[int, str, ExtractMethod, float]]:
    """
    For each native page, if ``needs_ocr`` run OCR and merge; else keep native.

    Returns:
        List of (page_number, text, method, confidence) in page order.
    """
    svc = ocr_service or get_default_ocr_service()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    results: list[tuple[int, str, ExtractMethod, float]] = []
    try:
        if len(native_pages) != doc.page_count:
            raise ValueError("native_pages length must match PDF page count")

        for i, np in enumerate(native_pages):
            page = doc.load_page(i)
            pnum = np.page_number
            if not np.needs_ocr:
                results.append((pnum, np.text, ExtractMethod.PARSE, 1.0))
                continue

            if not svc.provider.is_available():
                logger.warning(
                    "Page %s flagged for OCR but provider %s unavailable",
                    pnum,
                    svc.provider.provider_id,
                )
                results.append(
                    (
                        pnum,
                        np.text,
                        ExtractMethod.PARSE,
                        0.3 if np.text else 0.0,
                    ),
                )
                continue

            ocr_text, ocr_conf, _ = ocr_single_pdf_page(page, pnum, ocr_service=svc)
            merged, method, conf = merge_native_and_ocr_text(np.text, ocr_text, ocr_conf)
            results.append((pnum, merged, method, conf))
    finally:
        doc.close()
    return results
