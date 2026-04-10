"""Excel export via :class:`~vantage_preprocess.export.xlsx_exporter.XlsxVantageExporter`."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from vantage_preprocess.export.ingestion_record import ingestion_records_from_export_rows
from vantage_preprocess.export.xlsx_exporter import XlsxVantageExporter
from vantage_preprocess.models.document import ExportRow


def write_excel(
    rows: list[ExportRow],
    path: Path,
    *,
    semantic_document_type: str | None = None,
    processing_timestamp: datetime | None = None,
) -> None:
    """Write ``.xlsx`` with string cells and formula-injection mitigation on text fields."""
    ing = ingestion_records_from_export_rows(
        rows,
        semantic_document_type=semantic_document_type,
        processing_timestamp=processing_timestamp,
    )
    XlsxVantageExporter().write(ing, path)
