"""Helpers to classify from pipeline :class:`StructuredDocument` objects."""

from __future__ import annotations

from vantage_preprocess.classification.base import DocumentClassifier
from vantage_preprocess.classification.heuristic import HeuristicDocumentClassifier
from vantage_preprocess.classification.models import ClassificationResult
from vantage_preprocess.models.document import StructuredDocument

_default: HeuristicDocumentClassifier | None = None


def get_default_classifier() -> DocumentClassifier:
    global _default
    if _default is None:
        _default = HeuristicDocumentClassifier()
    return _default


def classify_structured_document(
    doc: StructuredDocument,
    *,
    classifier: DocumentClassifier | None = None,
) -> ClassificationResult:
    """Concatenate page text and run the classifier (same as one big body)."""
    clf = classifier or get_default_classifier()
    text = "\n\n".join(p.text for p in doc.pages)
    return clf.classify(source_filename=doc.source_filename, text=text)
