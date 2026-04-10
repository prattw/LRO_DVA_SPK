"""
Image/PDF page OCR via :mod:`vantage_preprocess.ocr` (pluggable provider + preprocessing).

Legacy entrypoints ``ocr_pil_image`` and ``ocr_image_bytes`` return :class:`PageText`.
"""

from __future__ import annotations

from PIL import Image

from vantage_preprocess.models.document import PageText
from vantage_preprocess.models.enums import ExtractMethod
from vantage_preprocess.ocr import get_default_ocr_service
from vantage_preprocess.utils.text import normalize_whitespace


def tesseract_available() -> bool:
    """Whether the current default OCR provider reports it can run (local Tesseract or cloud)."""
    return get_default_ocr_service().provider.is_available()


def ocr_pil_image(img: Image.Image, page_number: int) -> PageText:
    """Run default OCR service on a PIL image; returns :class:`PageText` for chunking."""
    svc = get_default_ocr_service()
    r = svc.ocr_pil(img, page_number)
    text = normalize_whitespace(r.text)
    conf = r.confidence if not r.error else 0.0
    return PageText(
        page_number=page_number,
        text=text,
        method=ExtractMethod.OCR,
        confidence=min(1.0, max(0.0, conf)),
    )


def ocr_image_bytes(data: bytes, page_number: int = 1) -> PageText:
    """Decode image bytes and OCR (single-page image files)."""
    svc = get_default_ocr_service()
    r = svc.ocr_image_bytes(data, page_number)
    text = normalize_whitespace(r.text)
    conf = r.confidence if not r.error else 0.0
    return PageText(
        page_number=page_number,
        text=text,
        method=ExtractMethod.OCR,
        confidence=min(1.0, max(0.0, conf)),
    )
