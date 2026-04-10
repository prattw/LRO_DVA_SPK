"""Heading and section detection for construction/engineering documents."""

from vantage_preprocess.sections.detect import detect_sections
from vantage_preprocess.sections.models import (
    DocumentSection,
    HeadingSource,
    SectionDetectionResult,
)

__all__ = [
    "DocumentSection",
    "HeadingSource",
    "SectionDetectionResult",
    "detect_sections",
]
