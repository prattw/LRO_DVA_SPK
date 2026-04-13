#!/usr/bin/env python3
"""
Split one PDF into multiple PDFs so each output is at most ``max_bytes`` (binary size on disk).

Uses PyMuPDF (same as ``vantage_preprocess``). Greedy: extend page range until the next
page would exceed the cap, then start a new part.

Usage:
  python examples/split_pdf_max_bytes.py INPUT.pdf ./out_parts --max-mb 5

This is separate from the preprocessing pipeline, which caps *portal .txt* size via
``VANTAGE_PORTAL_TXT_MAX_BYTES``, not source PDFs.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import fitz


def split_pdf_max_bytes(src: Path, out_dir: Path, max_bytes: int, prefix: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(src)
    written: list[Path] = []
    start = 0
    part = 0
    while start < doc.page_count:
        lo, hi = start + 1, doc.page_count
        best = start
        while lo <= hi:
            mid = (lo + hi) // 2
            trial = fitz.open()
            trial.insert_pdf(doc, from_page=start, to_page=mid - 1)
            try:
                blob = trial.tobytes(deflate=True, garbage=4)
            finally:
                trial.close()
            if len(blob) <= max_bytes:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if best == start:
            raise RuntimeError(
                f"A single page exceeds max_bytes ({max_bytes}): page {start} in {src}. "
                "Lower resolution or split the page outside this tool."
            )
        out = fitz.open()
        out.insert_pdf(doc, from_page=start, to_page=best - 1)
        part_path = out_dir / f"{prefix}_part{part + 1:03d}.pdf"
        try:
            out.save(
                part_path,
                deflate=True,
                garbage=4,
            )
        finally:
            out.close()
        written.append(part_path)
        part += 1
        start = best
    doc.close()
    return written


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input_pdf", type=Path, help="Source PDF")
    p.add_argument("out_dir", type=Path, help="Directory for part PDFs")
    p.add_argument(
        "--max-mb",
        type=float,
        default=5.0,
        help="Maximum size per output file in MiB (default: 5)",
    )
    p.add_argument(
        "--prefix",
        type=str,
        default="",
        help="Filename prefix for parts (default: stem of input)",
    )
    args = p.parse_args()
    max_bytes = int(args.max_mb * 1024 * 1024)
    prefix = args.prefix or args.input_pdf.stem
    paths = split_pdf_max_bytes(args.input_pdf.resolve(), args.out_dir.resolve(), max_bytes, prefix)
    for q in paths:
        print(q, q.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
