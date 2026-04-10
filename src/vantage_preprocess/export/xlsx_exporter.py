"""Excel exporter: ``.xlsx`` with string cells and formula-injection mitigation."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from vantage_preprocess.export.base_exporter import BaseVantageExporter
from vantage_preprocess.export.ingestion_record import VantageIngestionRecord
from vantage_preprocess.export.sanitize import (
    sanitize_excel_cell,
    strip_control_chars_except_newline_tab,
)


class XlsxVantageExporter(BaseVantageExporter):
    """Write ingestion rows to a single worksheet (``chunks``)."""

    sheet_title: str = "chunks"

    def write(self, rows: Sequence[VantageIngestionRecord], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.title = self.sheet_title
        ws.append(list(self.columns))
        for cell in ws[1]:
            cell.font = Font(bold=True)

        for r in rows:
            st = r.section_title
            if st is not None:
                st = strip_control_chars_except_newline_tab(st)
            ct = strip_control_chars_except_newline_tab(r.chunk_text)
            ws.append(
                [
                    r.document_id,
                    r.source_filename,
                    r.original_file_type,
                    r.chunk_id,
                    r.page_start,
                    r.page_end,
                    sanitize_excel_cell(st) if st is not None else "",
                    r.document_type,
                    r.extraction_method,
                    r.extraction_confidence,
                    r.extraction_mode,
                    r.ocr_used,
                    r.ocr_confidence if r.ocr_confidence is not None else "",
                    r.percent_empty_pages,
                    r.section_detection_confidence
                    if r.section_detection_confidence is not None
                    else "",
                    r.chunk_quality_score,
                    r.low_quality_chunk,
                    r.document_needs_review,
                    sanitize_excel_cell(ct),
                    r.processing_timestamp.isoformat(),
                ],
            )

        wb.save(path)
