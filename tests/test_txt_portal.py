"""Portal .txt export for Army Vantage web upload."""

from __future__ import annotations

from pathlib import Path

from vantage_preprocess.export.txt_portal import write_txt_portal_files
from vantage_preprocess.models.document import ExportRow
from vantage_preprocess.models.enums import DocumentType, ExtractMethod


def _row(chunk_text: str, chunk_id: str = "a" * 32 + "-chunk-0001") -> ExportRow:
    return ExportRow(
        schema_version="3",
        document_id="a" * 32,
        source_filename="Spec_Volume.pdf",
        page_start=1,
        page_end=2,
        section_title="PART 2 PRODUCTS",
        chunk_id=chunk_id,
        chunk_text=chunk_text,
        document_type=DocumentType.PDF,
        confidence=0.95,
        extracted_method=ExtractMethod.PARSE,
    )


def test_txt_portal_writes_utf8_files(tmp_path: Path) -> None:
    n, dest = write_txt_portal_files(
        [_row("Hello world.")],
        tmp_path,
        max_bytes_per_file=1024 * 1024,
    )
    assert n == 1
    txts = list(dest.glob("*.txt"))
    assert len(txts) == 1
    text = txts[0].read_text(encoding="utf-8")
    assert "Hello world." in text
    assert "chunk_id:" in text
    assert "Spec_Volume.pdf" in text
    assert "PART 2 PRODUCTS" in text


def test_txt_portal_splits_oversized_chunk(tmp_path: Path) -> None:
    body = "word " * 5000
    n, dest = write_txt_portal_files(
        [_row(body)],
        tmp_path,
        max_bytes_per_file=4096,
    )
    assert n >= 2
    assert len(list(dest.glob("*.txt"))) == n
    for p in sorted(dest.glob("*.txt")):
        assert len(p.read_bytes()) <= 4096
