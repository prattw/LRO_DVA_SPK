"""
Plain UTF-8 ``.txt`` exports for Army Vantage web upload.

The Agent Studio uploader accepts PDFs, Office documents, presentations, and **text files**;
tabular JSON/CSV/JSONL are filtered out. This module writes one ``.txt`` per logical chunk
(with optional splitting when UTF-8 size exceeds a per-file cap).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from vantage_preprocess.export.ingestion_record import (
    VantageIngestionRecord,
    ingestion_records_from_export_rows,
)
from vantage_preprocess.export.sanitize import strip_control_chars_except_newline_tab

if TYPE_CHECKING:
    from vantage_preprocess.models.document import ExportRow


def _safe_stem(filename: str, max_len: int = 48) -> str:
    stem = Path(filename).stem
    s = "".join(c if c.isalnum() or c in "._-" else "_" for c in stem)
    s = re.sub(r"_+", "_", s).strip("._")
    if not s:
        s = "source"
    return s[:max_len]


def _split_utf8_by_max_bytes(text: str, max_bytes: int) -> list[str]:
    """Split ``text`` into segments, each encoding to at most ``max_bytes`` UTF-8 octets."""
    if max_bytes < 64:
        msg = "max_bytes must be at least 64 for practical text splits"
        raise ValueError(msg)
    data = text.encode("utf-8")
    if len(data) <= max_bytes:
        return [text]
    parts: list[str] = []
    i = 0
    while i < len(data):
        end = min(i + max_bytes, len(data))
        if end == len(data):
            parts.append(data[i:].decode("utf-8"))
            break
        while end > i and (data[end] & 0xC0) == 0x80:
            end -= 1
        if end == i:
            end = i + 1
            while end < len(data) and (data[end] & 0xC0) == 0x80:
                end += 1
        parts.append(data[i:end].decode("utf-8"))
        i = end
    return parts


def _header_lines(rec: VantageIngestionRecord, part: int | None, of: int | None) -> str:
    sec = rec.section_title
    if sec:
        sec = strip_control_chars_except_newline_tab(sec).replace("\n", " ").strip()
        if len(sec) > 500:
            sec = sec[:497] + "..."
    lines = [
        "# vantage_preprocess — Army Vantage portal text export (UTF-8)",
        f"# chunk_id: {rec.chunk_id}",
        f"# source: {rec.source_filename}",
        f"# pages: {rec.page_start}-{rec.page_end}",
    ]
    if sec:
        lines.append(f"# section: {sec}")
    if part is not None and of is not None and of > 1:
        lines.append(f"# split_part: {part} of {of}")
    lines.append("")
    return "\n".join(lines)


def write_txt_portal_files(
    rows: list[ExportRow],
    out_dir: Path,
    *,
    max_bytes_per_file: int,
    subdir_name: str = "vantage_portal_txt",
) -> tuple[int, Path]:
    """
    Write ``.txt`` files under ``out_dir / subdir_name``.

    Returns ``(files_written, dest_dir)``.
    """
    dest = out_dir / subdir_name
    dest.mkdir(parents=True, exist_ok=True)
    if not rows:
        return 0, dest

    records = ingestion_records_from_export_rows(rows)
    file_idx = 0
    for seq, rec in enumerate(records, start=1):
        body = strip_control_chars_except_newline_tab(rec.chunk_text)
        header_worst = _header_lines(rec, 1, 2)
        header_budget = len(header_worst.encode("utf-8")) + 64
        body_budget = max(256, max_bytes_per_file - header_budget)
        body_parts = _split_utf8_by_max_bytes(body, body_budget)
        n_parts = len(body_parts)

        for pi, segment in enumerate(body_parts, start=1):
            header = _header_lines(
                rec,
                pi if n_parts > 1 else None,
                n_parts if n_parts > 1 else None,
            )
            full = header + segment
            enc = full.encode("utf-8")
            if len(enc) > max_bytes_per_file:
                over = len(enc) - max_bytes_per_file + 4
                seg_b = segment.encode("utf-8")
                if len(seg_b) > over:
                    segment = seg_b[:-over].decode("utf-8", errors="ignore")
                    while segment and (segment.encode("utf-8")[-1] & 0xC0) == 0x80:
                        segment = segment[:-1]
                    full = header + segment

            stem = _safe_stem(rec.source_filename)
            name = f"{file_idx:05d}_{stem}_p{rec.page_start}-{rec.page_end}_c{seq:04d}"
            if n_parts > 1:
                name += f"_part{pi:02d}of{n_parts:02d}"
            name += ".txt"
            (dest / name).write_text(full, encoding="utf-8")
            file_idx += 1

    return file_idx, dest
