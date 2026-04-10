"""Army Vantage chunking engine (section-aware + paragraph fallback)."""

from vantage_preprocess.chunking.config import ChunkingConfig
from vantage_preprocess.chunking.engine import ChunkingRunResult, build_export_rows, chunk_document
from vantage_preprocess.chunking.strategies import (
    ChunkingStrategy,
    ParagraphChunker,
    RawChunk,
    SectionAwareChunker,
)
from vantage_preprocess.chunking.validate import ChunkValidationReport, validate_chunks

__all__ = [
    "ChunkingConfig",
    "ChunkingRunResult",
    "ChunkingStrategy",
    "ChunkValidationReport",
    "ParagraphChunker",
    "RawChunk",
    "SectionAwareChunker",
    "build_export_rows",
    "chunk_document",
    "validate_chunks",
]
