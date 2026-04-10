"""Validate chunk word counts against Army Vantage policy."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from vantage_preprocess.chunking.config import ChunkingConfig
from vantage_preprocess.chunking.words import count_words

logger = logging.getLogger(__name__)


@dataclass
class ChunkValidationReport:
    """Warnings and hard failures from :func:`validate_chunks`."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_chunks(texts: list[str], cfg: ChunkingConfig) -> ChunkValidationReport:
    """
    Reject any chunk strictly over ``max_words``; warn on chunks under ``min_words`` except the
    last chunk.
    """
    rep = ChunkValidationReport()
    n = len(texts)
    for i, t in enumerate(texts):
        wc = count_words(t)
        is_last = i == n - 1
        if wc > cfg.max_words:
            msg = (
                f"Chunk {i + 1}/{n} exceeds max_words ({wc} > {cfg.max_words}); "
                "this should not happen after enforcement."
            )
            rep.errors.append(msg)
            logger.error(msg)
        elif wc < cfg.min_words and not is_last and wc > 0:
            msg = (
                f"Chunk {i + 1}/{n} is below min_words "
                f"({wc} < {cfg.min_words}) before document end."
            )
            rep.warnings.append(msg)
            logger.warning(msg)
        elif wc == 0 and not is_last:
            msg = f"Chunk {i + 1}/{n} is empty (non-terminal)."
            rep.warnings.append(msg)
            logger.warning(msg)
    return rep
