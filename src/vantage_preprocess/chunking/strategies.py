"""Chunking strategies: section-aware (primary) and paragraph (fallback)."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from vantage_preprocess.chunking.config import ChunkingConfig
from vantage_preprocess.chunking.merge_split import merge_adjacent_sections, split_oversized_section
from vantage_preprocess.models.document import StructuredDocument
from vantage_preprocess.services.sectionize import SectionBlock, section_blocks_from_document


@dataclass
class RawChunk:
    """One non-overlapping text segment before overlap is applied."""

    section_title: str | None
    text: str
    page_start: int
    page_end: int
    section_detection_confidence: float | None = None


class ChunkingStrategy(ABC):
    """Pluggable strategy that emits ordered :class:`RawChunk` segments."""

    def __init__(self, config: ChunkingConfig) -> None:
        self.config = config

    @abstractmethod
    def build_raw_chunks(self, doc: StructuredDocument) -> list[RawChunk]:
        ...


class SectionAwareChunker(ChunkingStrategy):
    """Use detected sections (PART, SECTION …), merge small, split large."""

    def build_raw_chunks(self, doc: StructuredDocument) -> list[RawChunk]:
        blocks = section_blocks_from_document(doc)
        if not blocks:
            return []
        return _blocks_to_raw_chunks(blocks, self.config)


class ParagraphChunker(ChunkingStrategy):
    """
    Fallback: treat each page paragraph as a synthetic section block, then reuse the same
    merge/split pipeline so paragraph boundaries are never cut mid-paragraph.
    """

    def build_raw_chunks(self, doc: StructuredDocument) -> list[RawChunk]:
        synthetic: list[SectionBlock] = []
        for pg in doc.pages:
            for para in re.split(r"\n\s*\n", pg.text):
                t = para.strip()
                if t:
                    synthetic.append(
                        SectionBlock(
                            section_title=None,
                            page_start=pg.page_number,
                            page_end=pg.page_number,
                            text=t,
                        ),
                    )
        if not synthetic:
            return []
        return _blocks_to_raw_chunks(synthetic, self.config)


def _blocks_to_raw_chunks(blocks: list[SectionBlock], cfg: ChunkingConfig) -> list[RawChunk]:
    merged = merge_adjacent_sections(blocks, cfg)
    out: list[RawChunk] = []
    for m in merged:
        parts = split_oversized_section(m.text, cfg)
        if not parts:
            continue
        for p in parts:
            out.append(
                RawChunk(
                    section_title=m.section_title,
                    text=p,
                    page_start=m.page_start,
                    page_end=m.page_end,
                    section_detection_confidence=m.section_detection_confidence,
                ),
            )
    return out
