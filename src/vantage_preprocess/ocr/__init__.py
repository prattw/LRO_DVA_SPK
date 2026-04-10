"""
Pluggable OCR: preprocessing, Tesseract provider, batch API, cloud hook.

Typical usage::

    from vantage_preprocess.ocr import get_default_ocr_service
    svc = get_default_ocr_service()
    result = svc.ocr_pil(pil_image, page_number=1)
"""

from vantage_preprocess.ocr.base import OcrProvider
from vantage_preprocess.ocr.models import ImagePreprocessConfig, OcrPageResult, OcrRequest
from vantage_preprocess.ocr.service import (
    OcrService,
    get_default_ocr_service,
    set_default_ocr_service,
)
from vantage_preprocess.ocr.stub_cloud import CloudOcrProvider
from vantage_preprocess.ocr.tesseract_provider import TesseractOcrProvider

__all__ = [
    "CloudOcrProvider",
    "ImagePreprocessConfig",
    "OcrPageResult",
    "OcrProvider",
    "OcrRequest",
    "OcrService",
    "TesseractOcrProvider",
    "get_default_ocr_service",
    "set_default_ocr_service",
]
