"""OCR module: preprocessing, pluggable provider, service."""

from __future__ import annotations

from PIL import Image

from vantage_preprocess.ocr.base import OcrProvider
from vantage_preprocess.ocr.models import ImagePreprocessConfig, OcrPageResult, OcrRequest
from vantage_preprocess.ocr.preprocess import preprocess_for_ocr
from vantage_preprocess.ocr.service import OcrService, set_default_ocr_service


class _FakeProvider(OcrProvider):
    @property
    def provider_id(self) -> str:
        return "fake"

    def is_available(self) -> bool:
        return True

    def ocr_image(self, image: Image.Image, request: OcrRequest) -> OcrPageResult:
        return OcrPageResult(
            text="ok",
            confidence=0.99,
            provider_id=self.provider_id,
            page_number=request.page_number,
        )


def test_preprocess_grayscale_makes_rgb() -> None:
    img = Image.new("RGBA", (20, 20), (100, 50, 200, 255))
    cfg = ImagePreprocessConfig(grayscale=True, auto_contrast=False, deskew=False, threshold="none")
    out = preprocess_for_ocr(img, cfg)
    assert out.mode == "RGB"


def test_ocr_service_batch() -> None:
    svc = OcrService(_FakeProvider(), ImagePreprocessConfig(deskew=False))
    imgs = [Image.new("RGB", (10, 10), color="white")] * 2
    reqs = [OcrRequest(page_number=i + 1) for i in range(2)]
    batch = list(zip(imgs, reqs, strict=True))
    results = svc.ocr_batch(batch)
    assert len(results) == 2
    assert results[0].text == "ok"


def test_set_default_ocr_service_restores() -> None:
    fake = OcrService(_FakeProvider(), ImagePreprocessConfig(deskew=False))
    set_default_ocr_service(fake)
    from vantage_preprocess.ocr import get_default_ocr_service

    assert get_default_ocr_service().provider.provider_id == "fake"
    set_default_ocr_service(None)
    # Recreates tesseract-backed default
    assert get_default_ocr_service().provider.provider_id == "tesseract"


def test_tesseract_provider_confidence_structure() -> None:
    from vantage_preprocess.ocr.tesseract_provider import TesseractOcrProvider

    p = TesseractOcrProvider()
    if not p.is_available():
        return
    img = Image.new("RGB", (200, 80), color="white")
    r = p.ocr_image(img, OcrRequest(page_number=1))
    assert r.provider_id == "tesseract"
    assert 0.0 <= r.confidence <= 1.0
