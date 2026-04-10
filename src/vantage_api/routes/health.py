"""Liveness and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Process is up."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, str]:
    """Ready to accept traffic (extend with DB/queue checks later)."""
    return {"status": "ready"}
