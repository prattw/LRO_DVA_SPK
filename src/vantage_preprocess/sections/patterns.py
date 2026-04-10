"""
Construction / engineering heading patterns (MasterFormat, PART/DIVISION, outlines).

Assumptions:
- Headings are usually one line (or two short lines merged in OCR); very long lines are body.
- CSI-style section numbers use spaces (``09 65 00``); we also allow compact ``096500``.
- ``PART N - TITLE`` and ``SECTION …`` are common in specs; we score rather than binary match
  so weak signals do not dominate long documents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Lines longer than this are rarely standalone headings (tables, wrapped body).
_MAX_HEADING_CHARS = 220

# Minimum score to treat a line as a heading candidate (scale arbitrary 0–10+).
_MIN_HEADING_SCORE = 2.5

# If this fraction of lines score as headings, text heuristics are considered unreliable.
_MAX_HEADING_LINE_FRACTION = 0.12

# Absolute cap on heading count before we treat as noise (TOC, forms).
_MAX_HEADING_COUNT_BEFORE_NOISE = 40


@dataclass(frozen=True)
class HeadingScore:
    score: float
    reasons: tuple[str, ...]


_RE_CSI_SECTION = re.compile(
    r"^\s*(SECTION|Section)\s+((?:\d{2}\s\d{2}\s\d{2})|(?:\d{6}))\b",
)
_RE_PART = re.compile(
    r"^\s*(PART|Part)\s+(\d+|[IVXLCDM]+)\s*[-–—]\s*(.+)$",
)
_RE_PART_SHORT = re.compile(
    r"^\s*(PART|Part)\s+(\d+|[IVXLCDM]+)\s*$",
)
_RE_DIVISION = re.compile(
    r"^\s*(DIVISION|Division)\s+(\d+|[IVXLCDM]+)\b",
)
# 1.0 INTRODUCTION or 1.1.2 Scope
_RE_NUMBERED_TITLE = re.compile(
    r"^\s*(\d{1,2}\.\d+(?:\.\d+)?)\s+(\S.{0,200})$",
)
# Bare outline number on its own (short)
_RE_NUMBERED_ALONE = re.compile(
    r"^\s*(\d{1,2}\.\d+(?:\.\d+)?)\s*$",
)
_RE_ARTICLE = re.compile(
    r"^\s*(ARTICLE|Article)\s+\d+",
)
# TOC / leaders
_RE_TOC_DOTS = re.compile(r"\.{3,}")


def score_line_as_heading(line: str) -> HeadingScore | None:
    """Return a score and reasons if ``line`` looks like a construction heading."""
    s = line.strip()
    if len(s) < 3 or len(s) > _MAX_HEADING_CHARS:
        return None
    if _RE_TOC_DOTS.search(s):
        return None

    reasons: list[str] = []
    score = 0.0

    csi = bool(_RE_CSI_SECTION.match(s))
    if csi:
        score += 6.0
        reasons.append("Matches CSI-style SECTION line (e.g. SECTION 09 65 00).")
    elif re.match(r"^\s*(SECTION|Section)\s+\S+", s) and len(s) < 120:
        score += 3.5
        reasons.append("SECTION keyword with identifier (non-CSI).")
    if _RE_PART.match(s):
        score += 5.5
        reasons.append("Matches PART N - TITLE pattern.")
    elif _RE_PART_SHORT.match(s):
        score += 3.0
        reasons.append("PART N without inline title (short line).")
    if _RE_DIVISION.match(s):
        score += 4.5
        reasons.append("Matches DIVISION heading pattern.")
    m_num = _RE_NUMBERED_TITLE.match(s)
    if m_num:
        score += 3.5
        reasons.append(f'Numbered outline with title ("{m_num.group(1)} …").')
    elif _RE_NUMBERED_ALONE.match(s) and len(s) < 40:
        score += 2.0
        reasons.append("Short numbered outline line (e.g. 1.0 / 1.1).")
    if _RE_ARTICLE.match(s):
        score += 4.0
        reasons.append("Matches ARTICLE N pattern.")

    # ALL CAPS short title (common in older specs); weak signal
    if (
        len(s) < 100
        and len(s) > 6
        and s.upper() == s
        and s.isascii()
        and any(c.isalpha() for c in s)
        and not s.endswith(".")
    ):
        score += 1.5
        reasons.append("Short ALL CAPS line (weak heading signal).")

    if score <= 0:
        return None
    return HeadingScore(score=score, reasons=tuple(reasons))


def quick_heading_check(line: str) -> bool:
    """Fast boolean check compatible with legacy :func:`~vantage_preprocess.utils.text` usage."""
    hs = score_line_as_heading(line)
    return hs is not None and hs.score >= _MIN_HEADING_SCORE


def min_heading_score() -> float:
    return _MIN_HEADING_SCORE


def heading_noise_thresholds() -> tuple[float, int]:
    """Max fraction of lines and max count before switching to page-level fallback."""
    return (_MAX_HEADING_LINE_FRACTION, _MAX_HEADING_COUNT_BEFORE_NOISE)
