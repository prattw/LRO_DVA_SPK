"""
Image preprocessing before OCR: grayscale, contrast, denoise, threshold, deskew.

Designed so a cloud provider can reuse the same hooks (same PIL ``Image`` in/out).
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from PIL import Image, ImageFilter, ImageOps

from vantage_preprocess.ocr.models import ImagePreprocessConfig

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def preprocess_for_ocr(image: Image.Image, config: ImagePreprocessConfig) -> Image.Image:
    """Apply configured transforms; always returns RGB for downstream OCR."""
    img = image
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    if config.grayscale:
        img = ImageOps.grayscale(img).convert("RGB")

    if config.auto_contrast:
        img = ImageOps.autocontrast(img, cutoff=1)

    if config.median_filter_radius > 0:
        r = config.median_filter_radius
        img = img.filter(ImageFilter.MedianFilter(size=max(3, r * 2 + 1)))

    if config.threshold == "simple":
        g = img.convert("L")
        # Global split — works without numpy
        img = g.point(lambda p: 255 if p > 135 else 0).convert("RGB")

    if config.deskew:
        img = _deskew_with_osd(img)

    return img


def _deskew_with_osd(img: Image.Image) -> Image.Image:
    """Rotate using Tesseract OSD when ``osd`` traineddata is installed."""
    try:
        import pytesseract
    except ImportError:
        return img

    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return img

    try:
        osd = pytesseract.image_to_osd(img, lang="osd")
    except Exception as e:
        logger.debug("OSD deskew unavailable: %s", e)
        return img

    m = re.search(r"Rotate:\s*(\d+)", osd)
    if not m:
        return img
    angle = int(m.group(1)) % 360
    if angle == 0:
        return img
    logger.debug("OSD suggests rotating %s° for deskew", angle)
    return img.rotate(angle, expand=True, fillcolor="white")
