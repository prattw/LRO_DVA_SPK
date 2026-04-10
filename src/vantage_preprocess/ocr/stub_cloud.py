"""
Placeholder for a cloud OCR provider (Azure, AWS Textract, Google Vision).

Subclass :class:`~vantage_preprocess.ocr.base.OcrProvider`, call the vendor HTTP API inside
:meth:`ocr_image`, map responses to :class:`~vantage_preprocess.ocr.models.OcrPageResult`,
and reuse :mod:`vantage_preprocess.ocr.preprocess` so preprocessing stays consistent.
"""

from __future__ import annotations

from PIL import Image

from vantage_preprocess.ocr.base import OcrProvider
from vantage_preprocess.ocr.models import OcrPageResult, OcrRequest


class CloudOcrProvider(OcrProvider):
    """
    Not implemented — replace with your vendor client.

    Typical pattern::

        def ocr_image(self, image, request):
            png = pil_to_bytes(image)
            resp = self._client.analyze_document(png, language=request.language)
            return OcrPageResult(text=resp.text, confidence=resp.avg_confidence, ...)
    """

    @property
    def provider_id(self) -> str:
        return "cloud_stub"

    def is_available(self) -> bool:
        return False

    def ocr_image(self, image: Image.Image, request: OcrRequest) -> OcrPageResult:
        raise NotImplementedError(
            "Implement CloudOcrProvider with your cloud OCR client and wire credentials via env.",
        )
