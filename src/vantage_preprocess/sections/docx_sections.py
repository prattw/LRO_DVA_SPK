"""Section boundaries from DOCX :class:`~vantage_preprocess.extract.schemas.DocxBlock` order."""

from __future__ import annotations

from vantage_preprocess.extract.schemas import DocxBlockKind, DocxExtractionResult
from vantage_preprocess.sections.models import DocumentSection, HeadingSource


def sections_from_docx_blocks(
    result: DocxExtractionResult,
) -> tuple[list[DocumentSection], list[str]]:
    """
    Split on Word heading styles.

    Paragraphs before the first heading become a preamble section (``heading_text`` is None).
    All sections share ``page_start`` / ``page_end`` = 1 (DOCX has no reliable page model here).
    """
    notes: list[str] = [
        "DOCX: page span is 1–1 (single logical stream; print pages not in file).",
    ]
    blocks = result.blocks
    if not blocks:
        return [], notes

    sections: list[DocumentSection] = []
    open_title: str | None = None
    open_style: str | None = None
    lines: list[str] = []

    def flush() -> None:
        if open_title is None and not lines:
            return
        body = "\n\n".join(lines).strip()
        style_note = f'Word style "{open_style}"' if open_style else "Word heading style"
        sections.append(
            DocumentSection(
                section_index=len(sections),
                heading_text=open_title,
                body_text=body,
                page_start=1,
                page_end=1,
                heading_source=HeadingSource.DOCX_STYLE,
                confidence=0.92 if open_title else 0.55,
                reasons=[f"{style_note}."],
            ),
        )

    for b in blocks:
        if b.kind == DocxBlockKind.HEADING:
            flush()
            open_title = b.text
            open_style = b.style_name
            lines = []
        else:
            lines.append(b.text)

    flush()

    return sections, notes
