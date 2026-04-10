"""
Placeholder for a future ML-based ``DocumentClassifier``.

Train a model on labeled chunks, implement :meth:`classify` to return
:class:`~vantage_preprocess.classification.models.ClassificationResult` with ``evidence``
populated from feature attributions (e.g. SHAP) or matched n-grams.
"""

from __future__ import annotations

from vantage_preprocess.classification.base import DocumentClassifier
from vantage_preprocess.classification.models import ClassificationResult, DocumentCategory


class MlDocumentClassifier(DocumentClassifier):
    """Not implemented — replace with joblib/torch wrapper when data is available."""

    @property
    def classifier_id(self) -> str:
        return "ml_stub"

    def classify(self, *, source_filename: str, text: str) -> ClassificationResult:
        _ = (source_filename, text)
        return ClassificationResult(
            category=DocumentCategory.UNKNOWN,
            confidence=0.0,
            classifier_id=self.classifier_id,
            evidence=[],
            scores={},
        )
