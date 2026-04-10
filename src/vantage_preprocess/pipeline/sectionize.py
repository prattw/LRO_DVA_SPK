"""Shim: use `vantage_preprocess.services.sectionize` instead."""

from vantage_preprocess.services.sectionize import (
    SectionBlock,
    pages_to_section_blocks,
    section_blocks_from_document,
)

__all__ = [
    "SectionBlock",
    "pages_to_section_blocks",
    "section_blocks_from_document",
]
