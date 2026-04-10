"""Sample previews for ingestion exports (documentation and operator visibility)."""

from __future__ import annotations

from collections.abc import Sequence

from vantage_preprocess.export.ingestion_record import VantageIngestionRecord
from vantage_preprocess.export.sanitize import truncate_for_preview


def format_ingestion_preview(
    rows: Sequence[VantageIngestionRecord],
    *,
    limit: int = 3,
    chunk_preview_chars: int = 120,
) -> str:
    """
    Build a monospace-friendly preview: header line plus up to ``limit`` rows with truncated
    ``chunk_text`` (full text remains in real export files).
    """
    hdr = (
        "document_id | source_filename | chunk_id | pages | "
        "document_type | chunk_text…"
    )
    lines = [hdr, "-" * 72]
    for r in rows[:limit]:
        ct = truncate_for_preview(r.chunk_text, chunk_preview_chars)
        line = (
            f"{r.document_id[:12]}… | {r.source_filename[:24]} | {r.chunk_id[-16:]} | "
            f"{r.page_start}-{r.page_end} | {r.document_type} | {ct}"
        )
        lines.append(line)
    if len(rows) > limit:
        lines.append(f"… and {len(rows) - limit} more row(s).")
    return "\n".join(lines)


# Static sample for documentation (no dependency on real documents).
SAMPLE_EXPORT_PREVIEW = """\
# Army Vantage — sample ingestion export (preview)

Columns (CSV / JSONL / XLSX):
  document_id, source_filename, original_file_type, chunk_id, page_start, page_end,
  section_title, document_type, extraction_method, extraction_confidence,
  chunk_text, processing_timestamp

Example JSONL line (pretty-printed):
{
  "document_id": "a1b2c3d4e5f6…",
  "source_filename": "spec_section_09_65_00.pdf",
  "original_file_type": "pdf",
  "chunk_id": "a1b2c3d4e5f6…-chunk-0001",
  "page_start": 1,
  "page_end": 3,
  "section_title": "PART 2 - PRODUCTS",
  "document_type": "specification_section",
  "extraction_method": "parse",
  "extraction_confidence": 0.98,
  "chunk_text": "…",
  "processing_timestamp": "2026-04-10T18:00:00+00:00"
}

CSV: UTF-8, RFC 4180-style quoting for fields containing quotes or newlines.
XLSX: Strings stored as text; leading =/+/-/@ in chunk_text prefixed to avoid formula injection.
"""
