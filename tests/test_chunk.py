from vantage_preprocess.chunking.config import ChunkingConfig
from vantage_preprocess.models.document import PageText, StructuredDocument
from vantage_preprocess.models.enums import DocumentType, ExtractMethod
from vantage_preprocess.services.chunking import structured_to_export_rows


def test_txt_chunks():
    doc = StructuredDocument(
        document_id="a" * 64,
        source_filename="t.txt",
        source_path="/tmp/t.txt",
        source_sha256="b" * 64,
        mime_type="text/plain",
        document_type=DocumentType.TXT,
        pages=[
            PageText(
                page_number=1,
                text="SECTION 1\nBody line one.\nBody line two.",
                method=ExtractMethod.PARSE,
                confidence=1.0,
            )
        ],
        overall_extract_method=ExtractMethod.PARSE,
        overall_confidence=1.0,
    )
    cfg = ChunkingConfig(min_words=10, max_words=200, overlap_words_low=0, overlap_words_high=0)
    rows = structured_to_export_rows(doc, cfg)
    assert len(rows) >= 1
    assert rows[0].page_start == 1
    assert rows[0].section_title is not None or rows[0].chunk_text
    assert rows[0].chunk_id.endswith("-chunk-0001")
    assert rows[0].chunk_index == 1
    assert rows[0].total_chunks == len(rows)
