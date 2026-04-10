"""Tests for Pydantic domain models (validation + legacy round-trip)."""

from __future__ import annotations

import pytest

from vantage_preprocess.models.document import ExportRow
from vantage_preprocess.models.enums import DocumentType, ExtractMethod
from vantage_preprocess.models.vantage_domain import (
    DetectedDocumentKind,
    ExportRecord,
    UploadedDocument,
)


def _hash64() -> str:
    return "a" * 64


def test_sha256_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        UploadedDocument(
            document_id="x" * 16,
            source_filename="f.pdf",
            original_file_type=DocumentType.PDF,
            byte_size=10,
            parent_document_hash="not-a-hash",
        )


def test_export_record_round_trip_legacy() -> None:
    h = _hash64()
    er = ExportRecord(
        document_id="d" * 32,
        source_filename="a.pdf",
        original_file_type=DocumentType.PDF,
        page_start=1,
        page_end=2,
        section_title="PART 1",
        chunk_id="c1ab",
        chunk_text="hello",
        extraction_method=ExtractMethod.PARSE,
        extraction_confidence=1.0,
        detected_document_type=DetectedDocumentKind.SPECIFICATION_SECTION,
        parent_document_hash=h,
    )
    legacy = er.to_legacy_export_row()
    assert isinstance(legacy, ExportRow)
    back = ExportRecord.from_legacy_export_row(legacy)
    assert back.document_id == er.document_id
    assert back.parent_document_hash == h
