from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from vantage_preprocess.config import PipelineConfig
from vantage_preprocess.export.csv_export import write_csv
from vantage_preprocess.export.excel import write_excel
from vantage_preprocess.export.jsonl import write_jsonl
from vantage_preprocess.export.txt_portal import write_txt_portal_files
from vantage_preprocess.models.document import ExportRow
from vantage_preprocess.models.result import BatchResult, ErrorRecord, PerFileOutcome
from vantage_preprocess.quality.scoring import summarize_job_quality
from vantage_preprocess.services.chunking import structured_to_export_rows
from vantage_preprocess.services.enrich import enrich_export_rows, enrich_failure_detail
from vantage_preprocess.services.extraction import extract_structured
from vantage_preprocess.services.intake_service import intake_from_path

logger = logging.getLogger(__name__)


def collect_paths(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        return []
    if recursive:
        return sorted(
            p
            for p in input_path.rglob("*")
            if p.is_file() and not p.name.startswith(".")
        )
    return sorted(p for p in input_path.iterdir() if p.is_file() and not p.name.startswith("."))


def run_batch(
    paths: list[Path],
    config: PipelineConfig,
    *,
    run_id: str,
    started_at: datetime,
    include_traceback_in_errors: bool = False,
    on_file_done: Callable[[int, int, int], None] | None = None,
) -> BatchResult:
    """
    Sync pipeline: intake → extract → sectionize/chunk → enrich (each path independent).

    ``on_file_done`` (optional): called after each input path with
    ``(files_finished_so_far, files_total, cumulative_chunk_rows)`` for progress UIs.
    """
    all_rows: list[ExportRow] = []
    errors: list[ErrorRecord] = []
    per_file: list[PerFileOutcome] = []
    total = len(paths)

    for path in paths:
        fn = path.name
        logger.info("Batch run_id=%s: start file=%s", run_id, fn)
        try:
            intake = intake_from_path(path, config.intake)
        except Exception as e:
            logger.exception("Intake failed for %s", fn)
            errors.append(
                ErrorRecord(
                    stage="intake",
                    message=str(e),
                    source_filename=fn,
                    detail=enrich_failure_detail(e, include_traceback_in_errors),
                ),
            )
            per_file.append(
                PerFileOutcome(
                    source_filename=fn,
                    success=False,
                    failure_stage="intake",
                    error_message=str(e),
                ),
            )
            if on_file_done:
                on_file_done(len(per_file), total, len(all_rows))
            continue

        try:
            doc = extract_structured(intake)
            chunk_rows = structured_to_export_rows(doc, config.chunk.sizing)
            chunk_rows = enrich_export_rows(chunk_rows, run_id=run_id)
            all_rows.extend(chunk_rows)
            n = len(chunk_rows)
            logger.info(
                "Batch run_id=%s: ok file=%s document_id=%s chunks=%s",
                run_id,
                intake.source_filename,
                intake.document_id,
                n,
            )
            per_file.append(
                PerFileOutcome(
                    source_filename=intake.source_filename,
                    success=True,
                    document_id=intake.document_id,
                    chunks_created=n,
                ),
            )
            if on_file_done:
                on_file_done(len(per_file), total, len(all_rows))
        except Exception as e:
            logger.exception("Extract/chunk failed for %s", intake.source_filename)
            errors.append(
                ErrorRecord(
                    stage="extract",
                    message=str(e),
                    source_filename=intake.source_filename,
                    document_id=intake.document_id,
                    detail=enrich_failure_detail(e, include_traceback_in_errors),
                ),
            )
            per_file.append(
                PerFileOutcome(
                    source_filename=intake.source_filename,
                    success=False,
                    document_id=intake.document_id,
                    failure_stage="extract",
                    error_message=str(e),
                ),
            )
            if on_file_done:
                on_file_done(len(per_file), total, len(all_rows))

    finished_at = datetime.now(UTC)
    qsum = summarize_job_quality(all_rows)
    if qsum.get("low_quality_chunks", 0):
        logger.warning(
            "Batch run_id=%s: %s low-quality chunk(s) (see row flags)",
            run_id,
            qsum["low_quality_chunks"],
        )
    logger.info("Batch run_id=%s: quality_summary=%s", run_id, qsum)
    return BatchResult(
        run_id=run_id,
        started_at=started_at,
        finished_at=finished_at,
        rows=all_rows,
        errors=errors,
        files_seen=len(paths),
        per_file=per_file,
    )


def write_batch_artifacts(
    batch: BatchResult,
    out_dir: Path,
    formats: list[str],
    *,
    combined_basename: str,
    input_display: str,
    portal_txt_max_bytes: int = 9_437_184,
    portal_txt_subdir: str = "vantage_portal_txt",
) -> Path:
    """Write JSONL/CSV/XLSX, optional portal ``.txt`` bundle, and run_manifest.json."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fmt_set = {f.strip().lower() for f in formats}
    if "jsonl" in fmt_set:
        write_jsonl(batch.rows, out_dir / f"{combined_basename}.jsonl")
    if "csv" in fmt_set:
        write_csv(batch.rows, out_dir / f"{combined_basename}.csv")
    if "xlsx" in fmt_set or "excel" in fmt_set:
        write_excel(batch.rows, out_dir / f"{combined_basename}.xlsx")

    portal_txt_files = 0
    portal_txt_path: str | None = None
    if "txt" in fmt_set:
        portal_txt_files, pdir = write_txt_portal_files(
            batch.rows,
            out_dir,
            max_bytes_per_file=portal_txt_max_bytes,
            subdir_name=portal_txt_subdir,
        )
        portal_txt_path = str(pdir.resolve())

    manifest = {
        "run_id": batch.run_id,
        "created_at": batch.finished_at.isoformat(),
        "started_at": batch.started_at.isoformat(),
        "input": input_display,
        "out_dir": str(out_dir.resolve()),
        "formats": sorted(fmt_set),
        "files_seen": batch.files_seen,
        "rows": batch.rows_written,
        "quality_summary": summarize_job_quality(batch.rows),
        "errors": [e.model_dump(mode="json") for e in batch.errors],
    }
    if "txt" in fmt_set:
        manifest["portal_txt"] = {
            "files_written": portal_txt_files,
            "max_bytes_per_file": portal_txt_max_bytes,
            "directory": portal_txt_path,
        }
    manifest_path = out_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path
