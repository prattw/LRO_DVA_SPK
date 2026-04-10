from enum import StrEnum


class DocumentType(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"
    XLSX = "xlsx"
    IMAGE = "image"
    UNKNOWN = "unknown"


class ExtractMethod(StrEnum):
    PARSE = "parse"
    OCR = "ocr"
    HYBRID = "hybrid"
