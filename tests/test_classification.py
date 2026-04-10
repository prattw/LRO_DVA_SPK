"""Heuristic document classification."""

from __future__ import annotations

from vantage_preprocess.classification.heuristic import HeuristicDocumentClassifier
from vantage_preprocess.classification.models import DocumentCategory


def test_filename_submittal() -> None:
    clf = HeuristicDocumentClassifier()
    r = clf.classify(
        source_filename="Submittal_09_62_29_Cork.pdf",
        text="Intro paragraph with little signal.",
    )
    assert r.category == DocumentCategory.SUBMITTAL
    assert any("filename" in e.rule_id for e in r.evidence)


def test_spec_keywords_and_structure() -> None:
    clf = HeuristicDocumentClassifier()
    body = """
    SECTION 03 30 00
    CAST-IN-PLACE CONCRETE

    PART 1 - GENERAL
    1.1 SUMMARY
    Related documents are listed in Division 01.
    Quality assurance requirements apply.
    """ * 2
    r = clf.classify(source_filename="drawing_set.pdf", text=body)
    assert r.category in (DocumentCategory.SPECIFICATION, DocumentCategory.MIXED_PACKAGE)
    assert r.confidence > 0.2


def test_empty_text_unknown() -> None:
    clf = HeuristicDocumentClassifier()
    r = clf.classify(source_filename="a.pdf", text="   ")
    assert r.category == DocumentCategory.UNKNOWN
