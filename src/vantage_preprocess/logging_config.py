from __future__ import annotations

import logging
import sys
from typing import Literal


def configure_logging(level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO") -> None:
    """Configure root logging for CLI and workers (structured-friendly)."""
    lvl = getattr(logging, level)
    root = logging.getLogger()
    root.setLevel(lvl)
    if not root.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"),
        )
        root.addHandler(h)
