"""Escape and normalize cell/text payloads for tabular and JSONL exports."""

from __future__ import annotations

import re

# Excel treats strings starting with these as formulas (CSV injection / formula injection).
_EXCEL_FORMULA_START = frozenset("=+-@")


def strip_control_chars_except_newline_tab(text: str) -> str:
    """Remove C0 control characters except \\t and \\n (safe for XML/JSON and many loaders)."""
    return "".join(ch for ch in text if ch in "\t\n" or ord(ch) >= 32 or ch in "\r")


def sanitize_excel_cell(text: str) -> str:
    """
    Prefix cells that would be interpreted as formulas in Excel.

    See OWASP guidance on CSV/Excel injection; leading ``'`` forces literal display.
    """
    if not text:
        return text
    first = text[0]
    if first in _EXCEL_FORMULA_START or (first == "\t" and len(text) > 1 and text[1] in "=+"):
        return "'" + text
    return text


def truncate_for_preview(text: str, max_chars: int = 160) -> str:
    """Single-line-ish preview with ellipsis."""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1] + "…"
