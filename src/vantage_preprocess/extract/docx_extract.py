"""
DOCX extraction: ordered paragraphs and headings (python-docx).

Word has no reliable page model in the file; output is one logical stream of blocks,
then flattened to a single synthetic page for compatibility with page-based chunking.
"""

from __future__ import annotations

import logging
from io import BytesIO

import docx
from docx.text.paragraph import Paragraph

from vantage_preprocess.extract.schemas import DocxBlock, DocxBlockKind, DocxExtractionResult

logger = logging.getLogger(__name__)


def classify_paragraph_kind(paragraph: Paragraph) -> DocxBlockKind:
    """Infer heading vs body from style name (Word heading styles)."""
    try:
        name = (paragraph.style.name if paragraph.style else "") or ""
    except (AttributeError, ValueError):
        name = ""
    name_lower = name.lower()
    if "heading" in name_lower or name.startswith("Heading"):
        return DocxBlockKind.HEADING
    return DocxBlockKind.PARAGRAPH


def extract_docx_blocks(content: bytes) -> DocxExtractionResult:
    """
    Walk document body in order; collect non-empty paragraphs with heading classification.

    Tables are not expanded here (paragraph order only).
    """
    doc = docx.Document(BytesIO(content))
    blocks: list[DocxBlock] = []
    order = 0
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if not t:
            continue
        kind = classify_paragraph_kind(p)
        style_name = None
        try:
            if p.style and p.style.name:
                style_name = p.style.name
        except (AttributeError, ValueError):
            pass
        blocks.append(
            DocxBlock(
                order_index=order,
                kind=kind,
                style_name=style_name,
                text=t,
            ),
        )
        order += 1

    n_head = sum(1 for b in blocks if b.kind == DocxBlockKind.HEADING)
    logger.info("DOCX extracted %s blocks (%s headings)", len(blocks), n_head)
    return DocxExtractionResult(blocks=blocks)
