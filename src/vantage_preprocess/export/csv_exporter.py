"""
CSV exporter: RFC 4180-style rows, UTF-8.

Quotes fields when needed (newlines / delimiters in ``chunk_text``).
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

from vantage_preprocess.export.base_exporter import BaseVantageExporter
from vantage_preprocess.export.ingestion_record import VantageIngestionRecord
from vantage_preprocess.export.sanitize import strip_control_chars_except_newline_tab


class CsvVantageExporter(BaseVantageExporter):
    """
    Write ingestion rows as CSV.

    - Encoding: UTF-8 (optional BOM for Excel double-click compatibility).
    - ``QUOTE_MINIMAL`` quotes fields only when required; ``chunk_text`` is quoted when it
      contains delimiters or newlines.
    """

    def __init__(self, *, utf8_bom: bool = False, lineterminator: str = "\n") -> None:
        self.utf8_bom = utf8_bom
        self.lineterminator = lineterminator

    def write(self, rows: Sequence[VantageIngestionRecord], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "w"
        encoding = self.encoding
        with path.open(mode, encoding=encoding, newline="") as f:
            if self.utf8_bom:
                f.write("\ufeff")
            w = csv.DictWriter(
                f,
                fieldnames=list(self.columns),
                quoting=csv.QUOTE_MINIMAL,
                lineterminator=self.lineterminator,
            )
            w.writeheader()
            for r in rows:
                w.writerow(_row_as_csv_dict(r))


def _csv_opt_float(v: float | None) -> str | float:
    return "" if v is None else v


def _row_as_csv_dict(r: VantageIngestionRecord) -> dict[str, str | int | float | bool]:
    st = r.section_title
    if st is not None:
        st = strip_control_chars_except_newline_tab(st)
    ct = strip_control_chars_except_newline_tab(r.chunk_text)
    return {
        "document_id": r.document_id,
        "source_filename": r.source_filename,
        "original_file_type": r.original_file_type,
        "chunk_id": r.chunk_id,
        "page_start": r.page_start,
        "page_end": r.page_end,
        "section_title": st if st is not None else "",
        "document_type": r.document_type,
        "extraction_method": r.extraction_method,
        "extraction_confidence": r.extraction_confidence,
        "extraction_mode": r.extraction_mode,
        "ocr_used": r.ocr_used,
        "ocr_confidence": _csv_opt_float(r.ocr_confidence),
        "percent_empty_pages": r.percent_empty_pages,
        "section_detection_confidence": _csv_opt_float(r.section_detection_confidence),
        "chunk_quality_score": r.chunk_quality_score,
        "low_quality_chunk": r.low_quality_chunk,
        "document_needs_review": r.document_needs_review,
        "chunk_text": ct,
        "processing_timestamp": r.processing_timestamp.isoformat(),
    }
