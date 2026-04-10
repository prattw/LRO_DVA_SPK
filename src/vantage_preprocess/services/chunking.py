from __future__ import annotations

from vantage_preprocess.chunking.config import ChunkingConfig
from vantage_preprocess.chunking.engine import ChunkingRunResult, build_export_rows, chunk_document
from vantage_preprocess.models.document import ExportRow, StructuredDocument
from vantage_preprocess.services.sectionize import section_blocks_from_document


def structured_to_export_rows(
    doc: StructuredDocument,
    config: ChunkingConfig | None = None,
) -> list[ExportRow]:
    """Turn a structured document into Vantage export rows (word limits + overlap)."""
    return build_export_rows(doc, config)


def structured_to_chunking_result(
    doc: StructuredDocument,
    config: ChunkingConfig | None = None,
) -> ChunkingRunResult:
    """Same as :func:`structured_to_export_rows` but includes validation and strategy metadata."""
    return chunk_document(doc, config)


def section_blocks_for_debug(doc: StructuredDocument):
    return section_blocks_from_document(doc)
