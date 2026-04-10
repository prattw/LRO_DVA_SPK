"""Shim: use `vantage_preprocess.services.chunking` instead."""

from vantage_preprocess.services.chunking import (
    section_blocks_for_debug,
    structured_to_export_rows,
)

__all__ = ["section_blocks_for_debug", "structured_to_export_rows"]
