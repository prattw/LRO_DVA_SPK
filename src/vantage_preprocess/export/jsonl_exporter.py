"""JSON Lines exporter: one UTF-8 JSON object per line, ``ensure_ascii=False`` for Unicode."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from vantage_preprocess.export.base_exporter import BaseVantageExporter
from vantage_preprocess.export.ingestion_record import VantageIngestionRecord
from vantage_preprocess.export.sanitize import strip_control_chars_except_newline_tab


class JsonlVantageExporter(BaseVantageExporter):
    """Write one compact JSON object per line (NDJSON / JSONL for loaders and streaming)."""

    def write(self, rows: Sequence[VantageIngestionRecord], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding=self.encoding, newline="\n") as f:
            for r in rows:
                obj = _row_as_json_obj(r)
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _row_as_json_obj(r: VantageIngestionRecord) -> dict[str, object]:
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
        "section_title": st,
        "document_type": r.document_type,
        "extraction_method": r.extraction_method,
        "extraction_confidence": r.extraction_confidence,
        "extraction_mode": r.extraction_mode,
        "ocr_used": r.ocr_used,
        "ocr_confidence": r.ocr_confidence,
        "percent_empty_pages": r.percent_empty_pages,
        "section_detection_confidence": r.section_detection_confidence,
        "chunk_quality_score": r.chunk_quality_score,
        "low_quality_chunk": r.low_quality_chunk,
        "document_needs_review": r.document_needs_review,
        "chunk_text": ct,
        "processing_timestamp": r.processing_timestamp.isoformat(),
    }
