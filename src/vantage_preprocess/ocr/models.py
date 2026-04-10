"""Pydantic models for OCR requests and results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImagePreprocessConfig(BaseModel):
    """
    Tunable image cleanup before OCR.

    All steps are optional; defaults favor clarity over speed for document scans.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    grayscale: bool = Field(
        default=True,
        description="Grayscale then RGB for engines that expect 3 channels.",
    )
    auto_contrast: bool = Field(
        default=True,
        description="Stretch histogram (PIL ImageOps.autocontrast).",
    )
    median_filter_radius: int = Field(
        default=0,
        ge=0,
        le=5,
        description="If > 0, apply median denoise with this radius (PIL rank filter).",
    )
    threshold: Literal["none", "simple"] = Field(
        default="none",
        description="simple = global threshold after grayscale (good for high-contrast scans).",
    )
    deskew: bool = Field(
        default=True,
        description="Use Tesseract OSD to estimate rotation when available.",
    )


class OcrRequest(BaseModel):
    """Per-page OCR invocation metadata."""

    model_config = ConfigDict(str_strip_whitespace=True)

    page_number: int = Field(ge=1)
    language: str = Field(
        default="eng",
        description="Tesseract language code(s), e.g. eng or eng+deu.",
    )


class OcrPageResult(BaseModel):
    """Page-level OCR output with confidence for Vantage-style provenance."""

    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(description="Normalized OCR text (may be empty on failure).")
    confidence: float = Field(ge=0.0, le=1.0, description="Estimated mean word confidence, 0–1.")
    provider_id: str = Field(description="Which backend produced this (e.g. tesseract, azure_ocr).")
    page_number: int = Field(ge=1)
    error: str | None = Field(default=None, description="Set when OCR failed completely.")
    word_count: int = Field(default=0, ge=0)
    mean_tesseract_confidence_percent: float | None = Field(
        default=None,
        description="Raw Tesseract mean confidence 0–100 when available.",
    )
