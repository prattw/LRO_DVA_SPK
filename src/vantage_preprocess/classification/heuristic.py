"""
Explainable heuristic classifier: filename tokens, keyword hits, headings, light structure.

Tuned for construction / AEC-style naming; adjust keyword banks for your corpus.
"""

from __future__ import annotations

import logging
import math
import re
from pathlib import PurePath

from vantage_preprocess.classification.base import DocumentClassifier
from vantage_preprocess.classification.models import (
    ClassificationEvidence,
    ClassificationResult,
    DocumentCategory,
)
from vantage_preprocess.utils.text import line_looks_like_heading

logger = logging.getLogger(__name__)

# (substring in filename lower, category, weight)
_FILENAME_HINTS: tuple[tuple[str, DocumentCategory, float], ...] = (
    ("submittal", DocumentCategory.SUBMITTAL, 3.0),
    ("submit", DocumentCategory.SUBMITTAL, 1.5),
    ("spec", DocumentCategory.SPECIFICATION, 2.0),
    ("specification", DocumentCategory.SPECIFICATION, 3.0),
    ("section", DocumentCategory.SPECIFICATION, 1.0),
    ("division", DocumentCategory.SPECIFICATION, 1.5),
    ("transmittal", DocumentCategory.TRANSMITTAL, 3.0),
    ("transmitt", DocumentCategory.TRANSMITTAL, 2.0),
    ("rfi", DocumentCategory.REVIEW_COMMENTS, 2.0),
    ("review", DocumentCategory.REVIEW_COMMENTS, 1.5),
    ("comment", DocumentCategory.REVIEW_COMMENTS, 1.5),
    ("ballot", DocumentCategory.REVIEW_COMMENTS, 1.0),
    ("correspondence", DocumentCategory.CORRESPONDENCE, 2.5),
    ("letter", DocumentCategory.CORRESPONDENCE, 1.0),
    ("memo", DocumentCategory.CORRESPONDENCE, 1.2),
    ("package", DocumentCategory.MIXED_PACKAGE, 1.5),
    ("volume", DocumentCategory.MIXED_PACKAGE, 1.0),
)

# category -> list of phrases to search in lowercased text (word boundaries optional)
_KEYWORD_BANK: dict[DocumentCategory, tuple[str, ...]] = {
    DocumentCategory.SPECIFICATION: (
        "section",
        "division",
        "part",
        "specification",
        "materials",
        "execution",
        "quality assurance",
        "related documents",
        "summary",
        "references",
    ),
    DocumentCategory.SUBMITTAL: (
        "submittal",
        "shop drawing",
        "product data",
        "certificates",
        "test reports",
        "submit for review",
        "resubmittal",
    ),
    DocumentCategory.TRANSMITTAL: (
        "transmittal",
        "transmitted",
        "cc:",
        "distribution",
        "record document",
        "issued for",
    ),
    DocumentCategory.REVIEW_COMMENTS: (
        "review",
        "comment",
        "resolution",
        "rfi",
        "ballot",
        "disapproved",
        "revise and resubmit",
        "approved as noted",
    ),
    DocumentCategory.CORRESPONDENCE: (
        "dear",
        "sincerely",
        "regards",
        "cc:",
        "subject:",
        "reference:",
        "pursuant",
    ),
    DocumentCategory.MIXED_PACKAGE: (
        "table of contents",
        "appendix",
        "attachment",
        "exhibit",
        "volume",
        "book",
    ),
}

# Lines suggesting spec sections (CSI-style)
_SPEC_HEADING = re.compile(
    r"^(section|part|division)\s+[\d.]+",
    re.IGNORECASE | re.MULTILINE,
)
_CSI_LINE = re.compile(r"^\d{2}\s?\d{2}\s?\d{2}", re.MULTILINE)


def _score_filename(
    name: str,
) -> tuple[dict[DocumentCategory, float], list[ClassificationEvidence]]:
    base = PurePath(name).name.lower()
    scores = {
        c: 0.0
        for c in DocumentCategory
        if c not in (DocumentCategory.UNKNOWN, DocumentCategory.MIXED_PACKAGE)
    }
    ev: list[ClassificationEvidence] = []
    for needle, cat, w in _FILENAME_HINTS:
        if needle in base:
            scores[cat] = scores.get(cat, 0.0) + w
            ev.append(
                ClassificationEvidence(
                    rule_id=f"filename:{needle}",
                    category=cat,
                    weight=w,
                    detail=f'Filename contains "{needle}" → +{w} toward {cat.value}',
                ),
            )
    return scores, ev


def _keyword_scores(
    text: str,
) -> tuple[dict[DocumentCategory, float], list[ClassificationEvidence]]:
    lower = text.lower()
    scores = {c: 0.0 for c in _KEYWORD_BANK}
    ev: list[ClassificationEvidence] = []
    for cat, phrases in _KEYWORD_BANK.items():
        for ph in phrases:
            n = lower.count(ph)
            if n > 0:
                # Diminishing returns for repeated boilerplate
                add = min(4.0, math.log1p(n) * 2.0)
                scores[cat] = scores.get(cat, 0.0) + add
                ev.append(
                    ClassificationEvidence(
                        rule_id=f"keyword:{cat.value}:{ph[:24]}",
                        category=cat,
                        weight=add,
                        detail=(
                            f'Phrase "{ph}" appears ~{n} time(s) '
                            f"→ +{add:.2f} toward {cat.value}"
                        ),
                    ),
                )
    return scores, ev


def _structure_scores(
    text: str,
) -> tuple[dict[DocumentCategory, float], list[ClassificationEvidence]]:
    scores: dict[DocumentCategory, float] = {}
    ev: list[ClassificationEvidence] = []
    lines = text.splitlines()
    headingish = sum(1 for ln in lines if line_looks_like_heading(ln))
    spec_hits = len(_SPEC_HEADING.findall(text))
    csi_hits = len(_CSI_LINE.findall(text))

    if spec_hits or csi_hits or headingish > 3:
        w = min(6.0, 1.5 * spec_hits + 1.0 * csi_hits + 0.2 * headingish)
        scores[DocumentCategory.SPECIFICATION] = scores.get(DocumentCategory.SPECIFICATION, 0.0) + w
        ev.append(
            ClassificationEvidence(
                rule_id="structure:spec_headings",
                category=DocumentCategory.SPECIFICATION,
                weight=w,
                detail=(
                    f"Found {spec_hits} SECTION/PART/DIVISION-style headings, "
                    f"{csi_hits} CSI-style prefixes, {headingish} heading-like lines → +{w:.2f}"
                ),
            ),
        )

    # Short transmittal cover: early keyword + few lines
    if "transmittal" in text.lower()[:2500] and len(lines) < 80:
        w = 2.0
        scores[DocumentCategory.TRANSMITTAL] = scores.get(DocumentCategory.TRANSMITTAL, 0.0) + w
        ev.append(
            ClassificationEvidence(
                rule_id="structure:short_transmittal",
                category=DocumentCategory.TRANSMITTAL,
                weight=w,
                detail="Early 'transmittal' mention in a relatively short document → +2.0",
            ),
        )

    return scores, ev


def _merge_scores(
    parts: list[tuple[dict[DocumentCategory, float], list[ClassificationEvidence]]],
) -> tuple[dict[DocumentCategory, float], list[ClassificationEvidence]]:
    total: dict[DocumentCategory, float] = {}
    evidence: list[ClassificationEvidence] = []
    for scores, ev in parts:
        for k, v in scores.items():
            total[k] = total.get(k, 0.0) + v
        evidence.extend(ev)
    return total, evidence


def _pick_winner(
    scores: dict[DocumentCategory, float],
    evidence: list[ClassificationEvidence],
) -> tuple[DocumentCategory, float, list[ClassificationEvidence]]:
    """Argmax with mixed-package rule when top-2 are close."""
    # Exclude UNKNOWN from raw scores — it is a fallback label only
    candidates = {
        k: v
        for k, v in scores.items()
        if k not in (DocumentCategory.UNKNOWN, DocumentCategory.MIXED_PACKAGE)
    }
    if not candidates:
        return DocumentCategory.UNKNOWN, 0.2, evidence

    ranked = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
    if ranked[0][1] <= 0:
        return DocumentCategory.UNKNOWN, 0.15, evidence
    best_cat, best_s = ranked[0]
    second_s = ranked[1][1] if len(ranked) > 1 else 0.0

    # Mixed: two strong categories within margin
    if len(ranked) > 1 and best_s > 0 and second_s > 0:
        if second_s >= 0.55 * best_s and best_s > 3.0:
            mixed_ev = ClassificationEvidence(
                rule_id="meta:mixed_signals",
                category=DocumentCategory.MIXED_PACKAGE,
                weight=best_s,
                detail=(
                    f"Top scores close ({best_cat.value}={best_s:.2f}, "
                    f"{ranked[1][0].value}={second_s:.2f}) → mixed_package"
                ),
            )
            conf = min(0.95, best_s / (best_s + second_s + 1e-6))
            return DocumentCategory.MIXED_PACKAGE, conf, evidence + [mixed_ev]

    # Confidence: softmax-like from best vs rest
    total_mass = sum(max(0.0, v) for v in candidates.values()) + 1e-6
    conf = min(0.99, best_s / total_mass)

    if best_s < 1.0:
        return DocumentCategory.UNKNOWN, min(0.5, conf), evidence

    return best_cat, conf, evidence


class HeuristicDocumentClassifier(DocumentClassifier):
    """Rule-based classifier; swap for :class:`MlDocumentClassifier` later."""

    @property
    def classifier_id(self) -> str:
        return "heuristic_v1"

    def classify(self, *, source_filename: str, text: str) -> ClassificationResult:
        if not text.strip():
            logger.debug("Empty text for classification: %s", source_filename)
            return ClassificationResult(
                category=DocumentCategory.UNKNOWN,
                confidence=0.1,
                classifier_id=self.classifier_id,
                evidence=[],
                scores={},
            )

        s1, e1 = _score_filename(source_filename)
        s2, e2 = _keyword_scores(text)
        s3, e3 = _structure_scores(text)

        merged, evidence = _merge_scores([(s1, e1), (s2, e2), (s3, e3)])
        cat, conf, evidence = _pick_winner(merged, evidence)

        evidence.sort(key=lambda x: abs(x.weight), reverse=True)

        scores_out = {k.value: round(v, 4) for k, v in merged.items()}
        scores_out["unknown"] = 0.0

        return ClassificationResult(
            category=cat,
            confidence=round(conf, 4),
            classifier_id=self.classifier_id,
            evidence=evidence[:25],
            scores=scores_out,
        )
