"""Map StructuredDocument to ExtractedPage."""

from __future__ import annotations

from vantage_preprocess.extract.engine import structured_document_to_extracted_pages
from vantage_preprocess.models.document import PageText, StructuredDocument
from vantage_preprocess.models.enums import DocumentType, ExtractMethod


def test_structured_document_to_extracted_pages() -> None:
    doc = StructuredDocument(
        document_id="a" * 32,
        source_filename="x.txt",
        source_path="/tmp/x",
        source_sha256="b" * 64,
        mime_type="text/plain",
        document_type=DocumentType.TXT,
        pages=[
            PageText(
                page_number=1,
                text="hello",
                method=ExtractMethod.PARSE,
                confidence=1.0,
            ),
        ],
        overall_extract_method=ExtractMethod.PARSE,
        overall_confidence=1.0,
    )
    eps = structured_document_to_extracted_pages(doc)
    assert len(eps) == 1
    assert eps[0].page_number == 1
    assert eps[0].text == "hello"
    assert eps[0].parent_document_hash == "b" * 64
