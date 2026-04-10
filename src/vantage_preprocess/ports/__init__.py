"""Protocol interfaces for swapping intake, OCR, export, etc."""

from vantage_preprocess.ports.protocols import (
    DocumentDetector,
    IntakeService,
    PipelineRunner,
    TextExtractionService,
)

__all__ = [
    "DocumentDetector",
    "IntakeService",
    "PipelineRunner",
    "TextExtractionService",
]
