"""
Abstract OCR provider — swap local Tesseract for a cloud API without changing callers.

Implement :meth:`ocr_image` and :meth:`is_available`; optionally override :meth:`ocr_batch`
for parallel HTTP calls.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from vantage_preprocess.ocr.models import OcrPageResult, OcrRequest


class OcrProvider(ABC):
    """Pluggable OCR backend (Tesseract, Azure Document Intelligence, Textract, …)."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Short id for logs and :class:`OcrPageResult` (e.g. ``tesseract``)."""

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider can run in the current environment (binaries, API keys)."""

    @abstractmethod
    def ocr_image(self, image: Image.Image, request: OcrRequest) -> OcrPageResult:
        """
        Run OCR on a PIL image (already RGB/L as needed).

        Implementations should catch internal failures and return an :class:`OcrPageResult`
        with ``error`` set rather than raising, unless the failure is unrecoverable.
        """

    def ocr_batch(self, items: list[tuple[Image.Image, OcrRequest]]) -> list[OcrPageResult]:
        """Default sequential batch; override for concurrent cloud requests."""
        return [self.ocr_image(img, req) for img, req in items]
