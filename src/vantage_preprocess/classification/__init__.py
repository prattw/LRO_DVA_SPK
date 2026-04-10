"""
Document / chunk classification (heuristic first, ML later).

Use :class:`HeuristicDocumentClassifier` for explainable rules; swap in
:class:`MlDocumentClassifier` when a model is trained.
"""

from vantage_preprocess.classification.base import DocumentClassifier
from vantage_preprocess.classification.heuristic import HeuristicDocumentClassifier
from vantage_preprocess.classification.ml_stub import MlDocumentClassifier
from vantage_preprocess.classification.models import (
    ClassificationEvidence,
    ClassificationResult,
    DocumentCategory,
)
from vantage_preprocess.classification.structured import (
    classify_structured_document,
    get_default_classifier,
)

__all__ = [
    "ClassificationEvidence",
    "ClassificationResult",
    "DocumentCategory",
    "DocumentClassifier",
    "HeuristicDocumentClassifier",
    "MlDocumentClassifier",
    "classify_structured_document",
    "get_default_classifier",
]
