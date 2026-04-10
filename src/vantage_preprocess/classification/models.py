"""Types for document / chunk classification (explainable + ML-ready)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DocumentCategory(StrEnum):
    """High-level document kinds for routing, filters, and Vantage metadata."""

    SPECIFICATION = "specification"
    SUBMITTAL = "submittal"
    TRANSMITTAL = "transmittal"
    REVIEW_COMMENTS = "review_comments"
    CORRESPONDENCE = "correspondence"
    MIXED_PACKAGE = "mixed_package"
    UNKNOWN = "unknown"


class ClassificationEvidence(BaseModel):
    """One explainable signal that contributed to the score."""

    model_config = ConfigDict(str_strip_whitespace=True)

    rule_id: str = Field(description="Stable id, e.g. filename:submittal or keyword:spec_section.")
    category: DocumentCategory = Field(description="Which label this evidence supports.")
    weight: float = Field(description="Contribution magnitude before normalization.")
    detail: str = Field(description="Human-readable explanation.")


class ClassificationResult(BaseModel):
    """Outcome of a classifier run (heuristic or future ML)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    category: DocumentCategory
    confidence: float = Field(ge=0.0, le=1.0, description="Winner strength vs alternatives.")
    classifier_id: str = Field(
        description="Which implementation produced this, e.g. heuristic_v1, sklearn_v1.",
    )
    evidence: list[ClassificationEvidence] = Field(
        default_factory=list,
        description="Signals that fired, sorted by |weight| descending when possible.",
    )
    scores: dict[str, float] = Field(
        default_factory=dict,
        description="Raw per-category scores before argmax (keys = DocumentCategory values).",
    )
