from __future__ import annotations

import mimetypes
from pathlib import Path

from vantage_preprocess.config import IntakeLimits
from vantage_preprocess.models.intake import IntakeRecord
from vantage_preprocess.utils.ids import document_id_from_bytes, file_sha256


def intake_from_path(path: Path, limits: IntakeLimits) -> IntakeRecord:
    """Read file, validate size/extension, compute ids."""
    if not path.is_file():
        raise ValueError(f"Not a regular file: {path}")
    st = path.stat()
    if limits.max_bytes is not None and st.st_size > limits.max_bytes:
        raise ValueError(
            f"File too large ({st.st_size} bytes); max {limits.max_bytes} bytes",
        )
    suf = path.suffix.lower()
    if limits.allowed_suffixes is not None:
        check = suf if suf else ""
        if check not in limits.allowed_suffixes:
            raise ValueError(f"Extension {suf!r} not in allowed set")

    data = path.read_bytes()
    name = path.name
    resolved = str(path.resolve())
    sha = file_sha256(data)
    did = document_id_from_bytes(data, name)
    mime, _ = mimetypes.guess_type(name)

    return IntakeRecord(
        document_id=did,
        source_filename=name,
        source_sha256=sha,
        byte_size=len(data),
        mime_type=mime,
        local_path=resolved,
    )
