"""CSV export (delegates to :class:`~vantage_preprocess.export.csv_exporter.CsvVantageExporter`)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from vantage_preprocess.export.csv_exporter import CsvVantageExporter
from vantage_preprocess.export.ingestion_record import ingestion_records_from_export_rows
from vantage_preprocess.models.document import ExportRow


def write_csv(
    rows: list[ExportRow],
    path: Path,
    *,
    semantic_document_type: str | None = None,
    processing_timestamp: datetime | None = None,
    utf8_bom: bool = False,
) -> None:
    """Write pipeline rows using the Army Vantage ingestion column set (UTF-8)."""
    ing = ingestion_records_from_export_rows(
        rows,
        semantic_document_type=semantic_document_type,
        processing_timestamp=processing_timestamp,
    )
    CsvVantageExporter(utf8_bom=utf8_bom).write(ing, path)
