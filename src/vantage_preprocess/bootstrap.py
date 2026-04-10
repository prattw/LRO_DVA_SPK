"""
Bootstrap helpers for loading optional YAML/TOML into pipeline config models.

Reserved for ``--config vantage.yaml`` style workflows; default CLI does not use this yet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Parse a YAML file into a plain dict (requires ``pyyaml``)."""
    import yaml

    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"Root of {path} must be a mapping")
    return data
