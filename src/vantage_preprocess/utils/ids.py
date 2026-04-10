from __future__ import annotations

import hashlib
import uuid


def file_sha256(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def document_id_from_bytes(content: bytes, source_name: str) -> str:
    """Stable id from file bytes + filename salt (same file same name -> same id)."""
    h = hashlib.sha256()
    h.update(content)
    h.update(b"|")
    h.update(source_name.encode("utf-8", errors="replace"))
    return h.hexdigest()


def new_chunk_id(document_id: str, seq: int) -> str:
    """Legacy compact id (first 16 hex chars of document id + sequence)."""
    return f"{document_id[:16]}:{seq:06d}"


def format_vantage_chunk_id(document_id: str, chunk_index: int) -> str:
    """
    Deterministic Army Vantage chunk id: ``{document_id}-chunk-{0001}`` (1-based index).

    The full ``document_id`` is preserved so ids stay unique and traceable across exports.
    """
    return f"{document_id}-chunk-{chunk_index:04d}"


def run_manifest_id() -> str:
    return str(uuid.uuid4())
