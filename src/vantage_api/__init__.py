"""
HTTP API package for Army Vantage document preprocessing (FastAPI).

Install with the ``api`` extra: ``pip install "vantage-preprocess[api]"``.

This package depends on ``vantage_preprocess`` for the core pipeline only—keep
routes thin and delegate to ``vantage_preprocess.services.pipeline``.
"""

__version__ = "0.1.0"
