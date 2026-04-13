"""
Stable “master” tabular export for downstream Workshop / ontology work.

Written alongside portal ``.txt`` chunks: same chunk rows, fewer columns, fixed names for
warehouse and graph loaders without reprocessing PDFs.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from vantage_preprocess.export.sanitize import strip_control_chars_except_newline_tab
from vantage_preprocess.models.document import ExportRow

# Column order is part of the contract — add new fields at the end only.
MASTER_FIELDS: tuple[str, ...] = (
    "source_file",
    "source_spec",
    "section_number",
    "section_title",
    "chunk_id",
    "chunk_text",
    "page_start",
    "page_end",
    "extraction_method",
)

_CSI_SECTION = re.compile(r"\b(\d{2}\s+\d{2}\s+\d{2})\b")
_DECIMAL_OUTLINE = re.compile(r"\b(\d+(?:\.\d+)+)\b")


def infer_source_spec(source_filename: str) -> str:
    """Default spec key: filename stem (override with richer rules later if needed)."""
    return Path(source_filename).stem


def infer_section_number(section_title: str | None) -> str | None:
    """
    Best-effort section id from a heading string (CSI triple, dotted outline, …).

    Returns ``None`` when nothing matches — not all chunks have a parseable section id.
    """
    if not section_title:
        return None
    s = section_title.strip()
    m = _CSI_SECTION.search(s)
    if m:
        return re.sub(r"\s+", " ", m.group(1).strip())
    m = _DECIMAL_OUTLINE.search(s)
    if m:
        return m.group(1)
    return None


def export_row_to_master_dict(row: ExportRow) -> dict[str, Any]:
    """Map pipeline row to the fixed master schema."""
    title = row.section_title
    st = strip_control_chars_except_newline_tab(title) if title else None
    ct = strip_control_chars_except_newline_tab(row.chunk_text)
    sec_num = infer_section_number(title)
    return {
        "source_file": row.source_filename,
        "source_spec": infer_source_spec(row.source_filename),
        "section_number": sec_num,
        "section_title": st,
        "chunk_id": row.chunk_id,
        "chunk_text": ct,
        "page_start": row.page_start,
        "page_end": row.page_end,
        "extraction_method": row.extracted_method.value,
    }


def write_workshop_master(
    rows: list[ExportRow],
    out_dir: Path,
    *,
    basename: str = "vantage_master",
) -> tuple[Path | None, Path | None]:
    """
    Write ``{basename}.jsonl`` and ``{basename}.csv`` with :data:`MASTER_FIELDS`.

    Returns ``(jsonl_path, csv_path)`` or ``(None, None)`` when ``rows`` is empty.
    """
    if not rows:
        return None, None
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / f"{basename}.jsonl"
    csv_path = out_dir / f"{basename}.csv"

    records = [export_row_to_master_dict(r) for r in rows]

    with jsonl_path.open("w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(MASTER_FIELDS), extrasaction="ignore")
        w.writeheader()
        for rec in records:
            w.writerow({k: _csv_cell(rec.get(k)) for k in MASTER_FIELDS})

    return jsonl_path, csv_path


def _csv_cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)
