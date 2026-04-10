from __future__ import annotations

from pydantic import BaseModel, Field


class IntakeRecord(BaseModel):
    """Validated file identity after intake (local path now; API may use staging key)."""

    document_id: str
    source_filename: str
    source_sha256: str
    byte_size: int = Field(ge=0)
    mime_type: str | None = None
    local_path: str = Field(description="Absolute path to file on disk for this process")
