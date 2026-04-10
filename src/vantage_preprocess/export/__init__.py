"""
Army Vantage export: ingestion-shaped rows to CSV, JSONL, and XLSX, plus optional portal ``.txt`` files.

Use :class:`~vantage_preprocess.export.csv_exporter.CsvVantageExporter` and siblings for
class-based export; :func:`~vantage_preprocess.export.csv_export.write_csv` wraps them for
pipeline :class:`~vantage_preprocess.models.document.ExportRow` lists.
"""

from vantage_preprocess.export.base_exporter import BaseVantageExporter
from vantage_preprocess.export.csv_exporter import CsvVantageExporter
from vantage_preprocess.export.ingestion_record import (
    VantageIngestionRecord,
    ingestion_records_from_export_rows,
)
from vantage_preprocess.export.jsonl_exporter import JsonlVantageExporter
from vantage_preprocess.export.preview import SAMPLE_EXPORT_PREVIEW, format_ingestion_preview
from vantage_preprocess.export.txt_portal import write_txt_portal_files
from vantage_preprocess.export.xlsx_exporter import XlsxVantageExporter

__all__ = [
    "BaseVantageExporter",
    "CsvVantageExporter",
    "JsonlVantageExporter",
    "SAMPLE_EXPORT_PREVIEW",
    "VantageIngestionRecord",
    "XlsxVantageExporter",
    "format_ingestion_preview",
    "ingestion_records_from_export_rows",
    "write_txt_portal_files",
]
