"""
OCR service: preprocessing hooks + pluggable provider.

Use :func:`get_default_ocr_service` from PDF/image extractors; inject a custom
:class:`~vantage_preprocess.ocr.base.OcrProvider` for tests or cloud backends.
"""

from __future__ import annotations

import logging
from io import BytesIO

from PIL import Image

from vantage_preprocess.ocr.base import OcrProvider
from vantage_preprocess.ocr.models import ImagePreprocessConfig, OcrPageResult, OcrRequest
from vantage_preprocess.ocr.preprocess import preprocess_for_ocr
from vantage_preprocess.ocr.tesseract_provider import TesseractOcrProvider

logger = logging.getLogger(__name__)

_default_service: OcrService | None = None


class OcrService:
    """
    Applies :class:`ImagePreprocessConfig`, then delegates to an :class:`OcrProvider`.

    Thread-safe for read-only use after construction; create one service per provider/config.
    """

    def __init__(
        self,
        provider: OcrProvider,
        preprocess: ImagePreprocessConfig | None = None,
    ) -> None:
        self._provider = provider
        self._preprocess = preprocess or ImagePreprocessConfig()

    @property
    def provider(self) -> OcrProvider:
        return self._provider

    @property
    def preprocess(self) -> ImagePreprocessConfig:
        return self._preprocess

    def ocr_pil(
        self,
        image: Image.Image,
        page_number: int,
        *,
        language: str = "eng",
    ) -> OcrPageResult:
        req = OcrRequest(page_number=page_number, language=language)
        return self.ocr_with_request(image, req)

    def ocr_with_request(self, image: Image.Image, request: OcrRequest) -> OcrPageResult:
        prepared = preprocess_for_ocr(image, self._preprocess)
        try:
            return self._provider.ocr_image(prepared, request)
        except Exception as e:
            logger.error(
                "OCR pipeline error page=%s provider=%s: %s",
                request.page_number,
                self._provider.provider_id,
                e,
                exc_info=True,
            )
            return OcrPageResult(
                text="",
                confidence=0.0,
                provider_id=self._provider.provider_id,
                page_number=request.page_number,
                error=str(e),
            )

    def ocr_image_bytes(
        self,
        data: bytes,
        page_number: int,
        *,
        language: str = "eng",
    ) -> OcrPageResult:
        """Decode image file bytes (PNG, JPEG, TIFF, …) and run OCR."""
        try:
            img = Image.open(BytesIO(data)).convert("RGB")
        except Exception as e:
            logger.error(
                "Could not decode image for OCR page=%s: %s",
                page_number,
                e,
                exc_info=True,
            )
            return OcrPageResult(
                text="",
                confidence=0.0,
                provider_id=self._provider.provider_id,
                page_number=page_number,
                error=f"decode_failed: {e}",
            )
        return self.ocr_pil(img, page_number, language=language)

    def ocr_batch(
        self,
        items: list[tuple[Image.Image, OcrRequest]],
    ) -> list[OcrPageResult]:
        """Batch OCR; default provider runs sequentially — override for parallelism."""
        prepared: list[tuple[Image.Image, OcrRequest]] = [
            (preprocess_for_ocr(img, self._preprocess), req) for img, req in items
        ]
        return self._provider.ocr_batch(prepared)


def get_default_ocr_service() -> OcrService:
    """Singleton used by extractors unless you inject a custom service."""
    global _default_service
    if _default_service is None:
        _default_service = OcrService(TesseractOcrProvider())
    return _default_service


def set_default_ocr_service(service: OcrService | None) -> None:
    """Replace default (e.g. tests or cloud provider). Pass None to reset."""
    global _default_service
    _default_service = service
