"""Chunk word limits and export column contract."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from vantage_preprocess.chunking.config import ChunkingConfig
from vantage_preprocess.export.base_exporter import BaseVantageExporter
from vantage_preprocess.export.csv_export import write_csv
from vantage_preprocess.export.ingestion_record import ingestion_records_from_export_rows
from vantage_preprocess.models.document import PageText, StructuredDocument
from vantage_preprocess.models.enums import DocumentType, ExtractMethod
from vantage_preprocess.services.chunking import structured_to_export_rows

pytestmark = pytest.mark.integration


def test_all_chunks_respect_max_words() -> None:
    """Engine must never emit chunks above ``max_words`` (hard ceiling)."""
    body = "word " * 5_000
    doc = StructuredDocument(
        document_id="a" * 32,
        source_filename="big.txt",
        source_path="/x",
        source_sha256="b" * 64,
        mime_type="text/plain",
        document_type=DocumentType.TXT,
        pages=[
            PageText(
                page_number=1,
                text=body,
                method=ExtractMethod.PARSE,
                confidence=1.0,
            ),
        ],
        overall_extract_method=ExtractMethod.PARSE,
        overall_confidence=1.0,
    )
    cfg = ChunkingConfig(min_words=10, max_words=120, overlap_words_low=0, overlap_words_high=0)
    rows = structured_to_export_rows(doc, cfg)
    assert rows
    for r in rows:
        assert r.chunk_word_count <= cfg.max_words, (r.chunk_id, r.chunk_word_count)


def test_csv_columns_match_exporter_contract(tmp_path: Path) -> None:
    """Exported CSV header matches ``BaseVantageExporter.columns``."""
    doc = StructuredDocument(
        document_id="a" * 32,
        source_filename="t.txt",
        source_path="/t",
        source_sha256="b" * 64,
        mime_type="text/plain",
        document_type=DocumentType.TXT,
        pages=[
            PageText(
                page_number=1,
                text="PART 1\n\n" + "hello " * 200,
                method=ExtractMethod.PARSE,
                confidence=1.0,
            ),
        ],
        overall_extract_method=ExtractMethod.PARSE,
        overall_confidence=1.0,
    )
    rows = structured_to_export_rows(doc, ChunkingConfig(min_words=20, max_words=200, overlap_words_low=0, overlap_words_high=0))
    out = tmp_path / "out.csv"
    write_csv(rows, out, semantic_document_type="unknown")
    header = out.read_text(encoding="utf-8").splitlines()[0]
    parsed = next(csv.reader([header]))
    assert parsed == list(BaseVantageExporter.columns)


def test_ingestion_record_has_quality_fields() -> None:
    doc = StructuredDocument(
        document_id="a" * 32,
        source_filename="t.txt",
        source_path="/t",
        source_sha256="b" * 64,
        mime_type="text/plain",
        document_type=DocumentType.TXT,
        pages=[
            PageText(page_number=1, text="x " * 300, method=ExtractMethod.PARSE, confidence=1.0),
        ],
        overall_extract_method=ExtractMethod.PARSE,
        overall_confidence=1.0,
    )
    rows = structured_to_export_rows(doc)
    ing = ingestion_records_from_export_rows(rows)
    r0 = ing[0]
    assert r0.chunk_quality_score >= 0.0
    assert r0.extraction_mode in ("native", "ocr", "hybrid")
    for col in (
        "chunk_quality_score",
        "extraction_mode",
        "percent_empty_pages",
        "low_quality_chunk",
    ):
        assert col in BaseVantageExporter.columns
