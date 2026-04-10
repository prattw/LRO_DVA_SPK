"""Structured section output for heading-based segmentation."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class HeadingSource(StrEnum):
    """How the section boundary / title was determined."""

    DOCX_STYLE = "docx_style"
    """Word heading styles (Heading 1–N, etc.)."""

    PATTERN = "pattern"
    """Regex / heuristic match on plain text (PDF, TXT, or DOCX without reliable styles)."""

    FALLBACK_PAGE = "fallback_page"
    """One section per page when heuristics are too noisy or ambiguous."""

    FALLBACK_SINGLE = "fallback_single"
    """Whole document as one section when no headings were found."""


class DocumentSection(BaseModel):
    """A heading-bounded region with page span and explainability fields."""

    model_config = ConfigDict(str_strip_whitespace=True)

    section_index: int = Field(ge=0, description="0-based order in the document.")
    heading_text: str | None = Field(
        default=None,
        max_length=4000,
        description="Detected heading line, if any.",
    )
    body_text: str = Field(description="Content under this heading until the next boundary.")
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    heading_source: HeadingSource
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this boundary/title.")
    reasons: list[str] = Field(
        default_factory=list,
        description="Short human-readable notes for audit (matched pattern, style name, …).",
    )

    def page_span(self) -> tuple[int, int]:
        return (self.page_start, self.page_end)


class SectionDetectionResult(BaseModel):
    """Result of :func:`~vantage_preprocess.sections.detect.detect_sections`."""

    model_config = ConfigDict(str_strip_whitespace=True)

    sections: list[DocumentSection] = Field(default_factory=list)
    strategy: str = Field(
        description=(
            "docx_styles | text_heuristic | fallback_page | fallback_single — "
            "which path produced sections."
        ),
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Global assumptions and fallback triggers.",
    )
