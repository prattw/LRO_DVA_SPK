from __future__ import annotations

import mimetypes
from pathlib import Path

from vantage_preprocess.extract.csv_file import extract_csv
from vantage_preprocess.extract.docx import extract_docx
from vantage_preprocess.extract.ocr import ocr_image_bytes
from vantage_preprocess.extract.pdf import extract_pdf
from vantage_preprocess.extract.txt import extract_txt
from vantage_preprocess.extract.xlsx_file import extract_xlsx
from vantage_preprocess.models.document import StructuredDocument
from vantage_preprocess.models.enums import DocumentType
from vantage_preprocess.models.intake import IntakeRecord
from vantage_preprocess.services.detection import guess_kind


def extract_structured(intake: IntakeRecord) -> StructuredDocument:
    """Route by detected kind and run format-specific extractors + OCR fallback inside PDF/image."""
    path = Path(intake.local_path)
    data = path.read_bytes()
    name = intake.source_filename
    spath = intake.local_path

    kind = guess_kind(path)
    if kind == "pdf":
        return extract_pdf(data, name, spath)
    if kind == "docx":
        return extract_docx(data, name, spath)
    if kind == "txt":
        return extract_txt(data, name, spath)
    if kind == "csv":
        return extract_csv(data, name, spath)
    if kind == "xlsx":
        return extract_xlsx(data, name, spath)
    if kind == "image":
        page = ocr_image_bytes(data, page_number=1)
        return StructuredDocument(
            document_id=intake.document_id,
            source_filename=name,
            source_path=spath,
            source_sha256=intake.source_sha256,
            mime_type=intake.mime_type
            or mimetypes.guess_type(name)[0]
            or "application/octet-stream",
            document_type=DocumentType.IMAGE,
            pages=[page],
            overall_extract_method=page.method,
            overall_confidence=page.confidence,
        )

    raise ValueError(f"Unsupported file type (kind={kind!r}): {path}")


def load_structured(path: Path) -> StructuredDocument:
    """Convenience: intake defaults + extract (used by CLI/tests)."""
    from vantage_preprocess.config import IntakeLimits
    from vantage_preprocess.services.intake_service import intake_from_path

    intake = intake_from_path(path, IntakeLimits())
    return extract_structured(intake)
