from __future__ import annotations

import mimetypes
from pathlib import Path


def guess_kind(path: Path) -> str:
    """Return logical kind: pdf, docx, txt, csv, xlsx, image, unknown."""
    suf = path.suffix.lower()
    if suf == ".pdf":
        return "pdf"
    if suf in (".docx",):
        return "docx"
    if suf in (".txt", ".md", ".log"):
        return "txt"
    if suf in (".csv", ".tsv"):
        return "csv"
    if suf in (".xlsx", ".xlsm"):
        return "xlsx"
    if suf in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"):
        return "image"
    mime, _ = mimetypes.guess_type(path.name)
    if mime == "application/pdf":
        return "pdf"
    if mime in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",):
        return "docx"
    if mime in ("text/csv", "application/csv"):
        return "csv"
    if mime in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel.sheet.macroEnabled.12",
    ):
        return "xlsx"
    if mime and mime.startswith("text/"):
        return "txt"
    if mime and mime.startswith("image/"):
        return "image"
    return "unknown"
