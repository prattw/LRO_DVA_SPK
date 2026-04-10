from __future__ import annotations

import traceback

from vantage_preprocess.models.document import ExportRow


def enrich_export_rows(
    rows: list[ExportRow],
    *,
    run_id: str | None = None,
) -> list[ExportRow]:
    """
    Metadata enrichment for Army Vantage export rows.

    Placeholder for future: language detection, project tags, redaction, etc.
    `run_id` reserved for correlation when you add a field to the schema.
    """
    _ = (run_id,)
    return rows


def enrich_failure_detail(exc: Exception, include_traceback: bool) -> str | None:
    if not include_traceback:
        return None
    return traceback.format_exc()
