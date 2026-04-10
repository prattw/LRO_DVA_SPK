"""JSONL export via :class:`~vantage_preprocess.export.jsonl_exporter.JsonlVantageExporter`."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from vantage_preprocess.export.ingestion_record import ingestion_records_from_export_rows
from vantage_preprocess.export.jsonl_exporter import JsonlVantageExporter, _row_as_json_obj
from vantage_preprocess.models.document import ExportRow


def write_jsonl(
    rows: list[ExportRow],
    path: Path,
    *,
    semantic_document_type: str | None = None,
    processing_timestamp: datetime | None = None,
) -> None:
    """Write one JSON object per line (UTF-8, ``ensure_ascii=False``)."""
    ing = ingestion_records_from_export_rows(
        rows,
        semantic_document_type=semantic_document_type,
        processing_timestamp=processing_timestamp,
    )
    JsonlVantageExporter().write(ing, path)


def append_jsonl(
    rows: list[ExportRow],
    path: Path,
    *,
    semantic_document_type: str | None = None,
    processing_timestamp: datetime | None = None,
) -> None:
    """Append JSONL records (creates file if missing)."""
    ing = ingestion_records_from_export_rows(
        rows,
        semantic_document_type=semantic_document_type,
        processing_timestamp=processing_timestamp,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        for r in ing:
            f.write(json.dumps(_row_as_json_obj(r), ensure_ascii=False) + "\n")
