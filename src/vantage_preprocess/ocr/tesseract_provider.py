"""Local OCR via Tesseract (pytesseract)."""

from __future__ import annotations

import logging

import pytesseract
from PIL import Image

from vantage_preprocess.ocr.base import OcrProvider
from vantage_preprocess.ocr.models import OcrPageResult, OcrRequest

logger = logging.getLogger(__name__)


def _mean_tesseract_confidence(image: Image.Image, lang: str) -> tuple[float, float | None]:
    """
    Mean word confidence from ``image_to_data`` (0–1) and raw 0–100 mean if available.
    """
    try:
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        confs = [int(c) for c in data["conf"] if str(c).isdigit() and int(c) >= 0]
        raw = sum(confs) / len(confs) if confs else None
        scaled = min(1.0, max(0.0, (raw / 100.0))) if raw is not None else 0.5
        return scaled, float(raw) if raw is not None else None
    except Exception as e:
        logger.debug("Could not read Tesseract confidence: %s", e)
        return 0.7, None


class TesseractOcrProvider(OcrProvider):
    """Default on-prem OCR; replace with a cloud :class:`OcrProvider` when needed."""

    @property
    def provider_id(self) -> str:
        return "tesseract"

    def is_available(self) -> bool:
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception as e:
            logger.debug("Tesseract not available: %s", e)
            return False

    def ocr_image(self, image: Image.Image, request: OcrRequest) -> OcrPageResult:
        lang = request.language
        if not self.is_available():
            err = "Tesseract binary or traineddata not available"
            logger.error(
                "OCR failure page=%s provider=%s: %s",
                request.page_number,
                self.provider_id,
                err,
            )
            return OcrPageResult(
                text="",
                confidence=0.0,
                provider_id=self.provider_id,
                page_number=request.page_number,
                error=err,
            )

        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        try:
            text = pytesseract.image_to_string(image, lang=lang)
        except Exception as e:
            logger.error(
                "Tesseract OCR failed page=%s lang=%s: %s",
                request.page_number,
                lang,
                e,
                exc_info=True,
            )
            return OcrPageResult(
                text="",
                confidence=0.0,
                provider_id=self.provider_id,
                page_number=request.page_number,
                error=str(e),
            )

        conf, raw_pct = _mean_tesseract_confidence(image, lang)
        wc = len(text.split())
        return OcrPageResult(
            text=text,
            confidence=conf,
            provider_id=self.provider_id,
            page_number=request.page_number,
            word_count=wc,
            mean_tesseract_confidence_percent=raw_pct,
        )
