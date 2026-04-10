"""Run the API with Uvicorn: ``python -m vantage_api`` or ``vantage-api``."""

from __future__ import annotations


def main() -> None:
    import uvicorn

    from vantage_api.settings import get_settings

    s = get_settings()
    uvicorn.run(
        "vantage_api.app:create_app",
        factory=True,
        host=s.api_host,
        port=s.api_port,
        reload=s.api_reload,
        log_level=s.log_level,
    )


if __name__ == "__main__":
    main()
