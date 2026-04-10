"""FastAPI dependencies (settings; extend with DB sessions and pipeline factories)."""

from __future__ import annotations

from functools import lru_cache

from vantage_api.settings import ApiSettings, get_settings


@lru_cache
def _cached_settings() -> ApiSettings:
    return get_settings()


def get_api_settings() -> ApiSettings:
    """Injected settings singleton per process."""
    return _cached_settings()


def clear_settings_cache() -> None:
    """Invalidate settings cache (e.g. after tests change environment variables)."""
    _cached_settings.cache_clear()
