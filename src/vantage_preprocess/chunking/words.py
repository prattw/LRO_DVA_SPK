"""Word counting and token estimates for chunk budgeting."""

from __future__ import annotations

import re


def count_words(text: str) -> int:
    """Count whitespace-separated tokens (approximate words)."""
    if not text or not text.strip():
        return 0
    return len(text.split())


def tail_words(text: str, n: int) -> str:
    """Last ``n`` words (for overlap prefixes)."""
    if n <= 0 or not text.strip():
        return ""
    w = text.split()
    if len(w) <= n:
        return text.strip()
    return " ".join(w[-n:])


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    """Split on sentence boundaries (best-effort)."""
    text = text.strip()
    if not text:
        return []
    parts = _SENTENCE_END.split(text)
    return [p.strip() for p in parts if p.strip()]
