"""
Abstract document classifier.

Implement :meth:`classify` for heuristics today; later, wrap a sklearn/torch model that
still populates :class:`~vantage_preprocess.classification.models.ClassificationEvidence`
from SHAP, attention, or rule-matched features for explainability.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from vantage_preprocess.classification.models import ClassificationResult


class DocumentClassifier(ABC):
    """Pluggable classifier for a filename + text slice (full document or one chunk)."""

    @property
    @abstractmethod
    def classifier_id(self) -> str:
        """Stable id for :class:`ClassificationResult.classifier_id`."""

    @abstractmethod
    def classify(self, *, source_filename: str, text: str) -> ClassificationResult:
        """
        Classify using filename and body text (may be truncated upstream).

        Must remain pure (no I/O) for unit testing unless subclass documents otherwise.
        """
