"""
Merge small sections; split large text (prefer paragraph/sentence boundaries).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from vantage_preprocess.chunking.config import ChunkingConfig
from vantage_preprocess.chunking.words import count_words
from vantage_preprocess.services.sectionize import SectionBlock


def _min_heading_confidence(a: float | None, b: float | None) -> float | None:
    """Conservative merge: prefer the lower heading confidence when combining blocks."""
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


@dataclass
class MergedSection:
    """Section-like unit after merging adjacent small blocks."""

    section_title: str | None
    text: str
    page_start: int
    page_end: int
    section_detection_confidence: float | None = None


def _join_titles(a: str | None, b: str | None) -> str | None:
    parts = [x for x in (a, b) if x]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} / {parts[1]}"


def merge_adjacent_sections(blocks: list[SectionBlock], cfg: ChunkingConfig) -> list[MergedSection]:
    """
    Merge consecutive sections when either side is under ``min_words`` and the union stays
    within ``max_words``.
    """
    if not blocks:
        return []
    out: list[MergedSection] = []
    cur = MergedSection(
        section_title=blocks[0].section_title,
        text=blocks[0].text,
        page_start=blocks[0].page_start,
        page_end=blocks[0].page_end,
        section_detection_confidence=blocks[0].heading_confidence,
    )
    for b in blocks[1:]:
        w_cur = count_words(cur.text)
        w_b = count_words(b.text)
        merged = f"{cur.text}\n\n{b.text}".strip()
        w_m = count_words(merged)
        merge_ok = (w_cur < cfg.min_words or w_b < cfg.min_words) and w_m <= cfg.max_words
        if merge_ok:
            cur = MergedSection(
                section_title=_join_titles(cur.section_title, b.section_title),
                text=merged,
                page_start=min(cur.page_start, b.page_start),
                page_end=max(cur.page_end, b.page_end),
                section_detection_confidence=_min_heading_confidence(
                    cur.section_detection_confidence,
                    b.heading_confidence,
                ),
            )
        else:
            out.append(cur)
            cur = MergedSection(
                section_title=b.section_title,
                text=b.text,
                page_start=b.page_start,
                page_end=b.page_end,
                section_detection_confidence=b.heading_confidence,
            )
    out.append(cur)
    return out


_PARA_SPLIT = re.compile(r"\n\s*\n")


def split_oversized_section(text: str, cfg: ChunkingConfig) -> list[str]:
    """
    Split text over ``max_words`` into multiple chunks, preferring paragraph breaks.

    If a paragraph still exceeds ``max_words``, :func:`_split_word_window` breaks at sentences
    when possible, then at word boundaries (never mid-word).
    """
    text = text.strip()
    if not text:
        return []
    wc = count_words(text)
    if wc <= cfg.max_words:
        return [text]

    paras = [p.strip() for p in _PARA_SPLIT.split(text) if p.strip()]
    if len(paras) <= 1:
        return _split_word_window(text, cfg)

    chunks: list[str] = []
    buf: list[str] = []
    buf_words = 0

    def flush() -> None:
        nonlocal buf, buf_words
        if buf:
            chunks.append("\n\n".join(buf).strip())
        buf = []
        buf_words = 0

    for para in paras:
        pw = count_words(para)
        if pw > cfg.max_words:
            flush()
            chunks.extend(_split_word_window(para, cfg))
            continue
        nl = 1 if buf else 0
        if buf_words + pw + nl <= cfg.max_words and (
            buf_words + pw <= cfg.target_words_high or buf_words < cfg.min_words
        ):
            buf.append(para)
            buf_words += pw
            continue
        if buf_words + pw + nl <= cfg.max_words:
            buf.append(para)
            buf_words += pw
            flush()
            continue
        flush()
        buf = [para]
        buf_words = pw

    flush()
    return [c for c in chunks if c]


def _split_word_window(text: str, cfg: ChunkingConfig) -> list[str]:
    """Split long text into <= ``max_words`` chunks using sentence boundaries when possible."""
    words = text.split()
    n = len(words)
    if n == 0:
        return []
    if n <= cfg.max_words:
        return [text.strip()]

    out: list[str] = []
    i = 0
    target = cfg.target_mid()
    while i < n:
        remaining = n - i
        if remaining <= cfg.max_words:
            out.append(" ".join(words[i:n]).strip())
            break

        max_end = min(i + cfg.max_words, n)
        ideal_end = min(i + target, max_end)
        chunk_text = " ".join(words[i:ideal_end])
        trimmed = _snap_end_to_sentence(chunk_text, words, i, ideal_end, max_end, cfg)
        used = len(trimmed.split())
        if used == 0:
            trimmed = " ".join(words[i : i + cfg.min_words])
            used = len(trimmed.split())
        if count_words(trimmed) > cfg.max_words:
            trimmed = " ".join(words[i : i + cfg.max_words])
            used = cfg.max_words
        out.append(trimmed.strip())
        i += used

    return [c for c in out if c]


def _snap_end_to_sentence(
    chunk_text: str,
    words: list[str],
    start: int,
    ideal_end: int,
    max_end: int,
    cfg: ChunkingConfig,
) -> str:
    """Prefer cutting after ``.?!`` within the last ~120 chars while keeping word limits."""
    if ideal_end >= len(words):
        return chunk_text.strip()
    window = chunk_text
    for pos in range(len(window) - 1, -1, -1):
        if window[pos] in ".!?" and (pos + 1 >= len(window) or window[pos + 1].isspace()):
            candidate = window[: pos + 1].strip()
            cw = count_words(candidate)
            if cfg.min_words <= cw <= cfg.max_words:
                return candidate
            if cw > cfg.max_words:
                break
    return " ".join(words[start:ideal_end]).strip()
