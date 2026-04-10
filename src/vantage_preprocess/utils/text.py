from __future__ import annotations

import re


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def line_looks_like_heading(line: str) -> bool:
    """Delegate to :mod:`vantage_preprocess.sections.patterns` (lazy import)."""
    from vantage_preprocess.sections.patterns import quick_heading_check

    return quick_heading_check(line)
