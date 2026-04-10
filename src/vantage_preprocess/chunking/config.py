"""Tunable limits for Army Vantage chunking (words + overlap)."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ChunkingConfig(BaseModel):
    """
    Word-based chunk sizing.

    **Token budget:** With ``words_per_token ≈ 0.75``, ``max_words=2000`` implies about
    2,667 tokens—under a typical ~2,700-token embedding cap for the same model family.
    """

    min_words: int = Field(
        default=500,
        ge=1,
        le=50_000,
        description="Soft floor (last chunk may be smaller).",
    )
    max_words: int = Field(
        default=2000,
        ge=100,
        le=50_000,
        description="Hard ceiling; never exceeded.",
    )
    target_words_low: int = Field(
        default=1200,
        ge=50,
        description="Preferred chunk size lower bound.",
    )
    target_words_high: int = Field(
        default=1500,
        ge=50,
        description="Preferred chunk size upper bound.",
    )
    overlap_words_low: int = Field(
        default=100,
        ge=0,
        description="Minimum cross-chunk overlap (words).",
    )
    overlap_words_high: int = Field(
        default=200,
        ge=0,
        description="Maximum cross-chunk overlap (words).",
    )
    words_per_token: float = Field(
        default=0.75,
        gt=0.0,
        le=2.0,
        description="Approximate words per token (for estimates only).",
    )

    @model_validator(mode="after")
    def _order(self) -> ChunkingConfig:
        if self.min_words > self.max_words:
            raise ValueError("min_words must be <= max_words")
        if self.target_words_low > self.target_words_high:
            raise ValueError("target_words_low must be <= target_words_high")
        if self.overlap_words_low > self.overlap_words_high:
            raise ValueError("overlap_words_low must be <= overlap_words_high")
        if self.overlap_words_high >= self.min_words:
            raise ValueError("overlap should be smaller than min_words to preserve signal")
        return self

    def target_mid(self) -> int:
        return (self.target_words_low + self.target_words_high) // 2

    def overlap_target(self) -> int:
        return (self.overlap_words_low + self.overlap_words_high) // 2

    def max_tokens_estimate(self) -> float:
        """Upper bound tokens if chunk at max_words."""
        return self.max_words / self.words_per_token
