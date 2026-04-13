"""Workshop / ontology master export (slim JSONL + CSV)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from vantage_preprocess.export.workshop_master import (
    MASTER_FIELDS,
    export_row_to_master_dict,
    infer_section_number,
    infer_source_spec,
    write_workshop_master,
)
from vantage_preprocess.models.document import ExportRow
from vantage_preprocess.models.enums import DocumentType, ExtractMethod


def _row(**kwargs: object) -> ExportRow:
    base = dict(
        schema_version="3",
        document_id="d" * 32,
        source_filename="09 62 29 - TILE.pdf",
        page_start=1,
        page_end=1,
        section_title=None,
        chunk_id="c1",
        chunk_text="body",
        document_type=DocumentType.PDF,
        confidence=0.9,
        extracted_method=ExtractMethod.PARSE,
    )
    base.update(kwargs)
    return ExportRow.model_validate(base)


def test_infer_section_number_csi() -> None:
    assert infer_section_number("SECTION 09 62 29 - CORK") == "09 62 29"


def test_infer_section_number_dotted() -> None:
    assert infer_section_number("1.2.3 Scope") == "1.2.3"


def test_infer_source_spec_stem() -> None:
    assert infer_source_spec("folder/Spec A (2024).pdf") == "Spec A (2024)"


def test_master_dict_maps_extract_method() -> None:
    r = _row(extracted_method=ExtractMethod.OCR, section_title="PART 1")
    d = export_row_to_master_dict(r)
    assert d["extraction_method"] == "ocr"
    assert d["source_file"] == "09 62 29 - TILE.pdf"
    assert d["source_spec"] == "09 62 29 - TILE"


def test_write_workshop_master_roundtrip(tmp_path: Path) -> None:
    rows = [_row(chunk_id="a", chunk_text='Say "hi"'), _row(chunk_id="b", chunk_text="x" * 3)]
    jp, cp = write_workshop_master(rows, tmp_path)
    assert jp is not None and cp is not None
    lines = jp.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    o0 = json.loads(lines[0])
    assert set(o0.keys()) == set(MASTER_FIELDS)

    with cp.open(encoding="utf-8", newline="") as f:
        dr = list(csv.DictReader(f))
    assert len(dr) == 2
    assert list(dr[0].keys()) == list(MASTER_FIELDS)


def test_write_empty_returns_none() -> None:
    jp, cp = write_workshop_master([], Path("."))
    assert jp is None and cp is None
