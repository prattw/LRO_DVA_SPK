"""Example: mock PDF extraction to assert OCR-style structured output without Tesseract."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from vantage_preprocess.models.document import PageText, StructuredDocument
from vantage_preprocess.models.enums import DocumentType, ExtractMethod
from vantage_preprocess.models.intake import IntakeRecord
from vantage_preprocess.services.extraction import extract_structured

pytestmark = pytest.mark.integration


def test_extract_pdf_can_return_ocr_pages_via_mock(tmp_path) -> None:
    """Force ``extract_pdf`` to return OCR pages — CI-friendly substitute for real scanned PDFs."""
    p = tmp_path / "scan.pdf"
    p.write_bytes(b"%PDF-1.4\n%EOF\n")

    fake = StructuredDocument(
        document_id="a" * 32,
        source_filename="scan.pdf",
        source_path=str(p),
        source_sha256="b" * 64,
        mime_type="application/pdf",
        document_type=DocumentType.PDF,
        pages=[
            PageText(
                page_number=1,
                text="ocr text from image",
                method=ExtractMethod.OCR,
                confidence=0.72,
            ),
        ],
        overall_extract_method=ExtractMethod.OCR,
        overall_confidence=0.72,
    )
    intake = IntakeRecord(
        document_id=fake.document_id,
        source_filename="scan.pdf",
        source_sha256=fake.source_sha256,
        byte_size=p.stat().st_size,
        mime_type="application/pdf",
        local_path=str(p.resolve()),
    )
    with patch("vantage_preprocess.services.extraction.extract_pdf", return_value=fake):
        out = extract_structured(intake)
    assert out.overall_extract_method == ExtractMethod.OCR
    assert out.pages[0].method == ExtractMethod.OCR
    assert out.pages[0].confidence == pytest.approx(0.72)
