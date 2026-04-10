"""Shim: use `vantage_preprocess.services.extraction` instead."""

from vantage_preprocess.services.extraction import extract_structured, load_structured

__all__ = ["extract_structured", "load_structured"]
