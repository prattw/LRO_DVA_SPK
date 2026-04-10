"""Cross-chunk overlap for retrieval continuity (capped so chunks stay within ``max_words``)."""

from __future__ import annotations

import logging

from vantage_preprocess.chunking.words import count_words, tail_words

logger = logging.getLogger(__name__)


def apply_overlap_safe(raw_chunks: list[str], overlap_words: int, max_words: int) -> list[str]:
    """
    Build display chunks from **non-overlapping** sequential segments.

    For ``i > 0``, prepend the last ``overlap_words`` words of raw segment ``i - 1`` to segment
    ``i``, then trim the new segment body so the total stays at or below ``max_words``.

    This keeps overlap in the 100–200 word range while respecting the hard ``max_words`` cap.
    """
    if not raw_chunks:
        return []
    if overlap_words <= 0:
        return [_cap_words(c, max_words) for c in raw_chunks]

    out: list[str] = []
    for i, seg in enumerate(raw_chunks):
        if i == 0:
            out.append(_cap_words(seg.strip(), max_words))
            continue
        prev_raw = raw_chunks[i - 1]
        tail = tail_words(prev_raw, overlap_words)
        tw = count_words(tail)
        body_words = seg.split()
        allow_body = max(0, max_words - tw)
        if allow_body < count_words(seg):
            logger.debug(
                "Overlap capped new words in chunk %s to %s (max_words=%s, tail_words=%s)",
                i + 1,
                allow_body,
                max_words,
                tw,
            )
        body = " ".join(body_words[:allow_body])
        combined = (tail + " " + body).strip() if tail else body
        out.append(combined)
    return out


def _cap_words(text: str, max_words: int) -> str:
    w = text.split()
    if len(w) <= max_words:
        return text.strip()
    return " ".join(w[:max_words]).strip()
