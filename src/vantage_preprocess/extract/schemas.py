"""Pydantic models for document extraction inputs/outputs (testable, JSON-serializable)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from vantage_preprocess.models.enums import ExtractMethod


class PdfNativePage(BaseModel):
    """Result of native (non-OCR) text extraction for one PDF page."""

    model_config = ConfigDict(str_strip_whitespace=True)

    page_number: int = Field(ge=1, description="1-based page index.")
    text: str = Field(description="Raw-ish text from PyMuPDF get_text.")
    non_whitespace_char_count: int = Field(ge=0)
    needs_ocr: bool = Field(
        description="True if text is missing or below sparsity threshold (flag for OCR pass).",
    )


class DocxBlockKind(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"


class DocxBlock(BaseModel):
    """One paragraph or heading in document order."""

    model_config = ConfigDict(str_strip_whitespace=True)

    order_index: int = Field(ge=0)
    kind: DocxBlockKind
    style_name: str | None = Field(default=None, description="Word style name when present.")
    text: str = Field(description="Non-empty paragraph or heading text.")


class DocxExtractionResult(BaseModel):
    """Ordered headings and paragraphs from a DOCX body."""

    blocks: list[DocxBlock] = Field(default_factory=list)

    def flattened_text(self, *, heading_prefix: str = "") -> str:
        """
        Single stream preserving order (one logical page for downstream chunking).

        Optional ``heading_prefix`` e.g. ``'# '`` for markdown-like headings.
        """
        lines: list[str] = []
        for b in self.blocks:
            if b.kind == DocxBlockKind.HEADING and heading_prefix:
                lines.append(f"{heading_prefix}{b.text}")
            else:
                lines.append(b.text)
        return "\n\n".join(lines)


class TxtExtractionPage(BaseModel):
    """Single logical page for plain text files."""

    page_number: int = 1
    text: str
    method: ExtractMethod = ExtractMethod.PARSE
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
