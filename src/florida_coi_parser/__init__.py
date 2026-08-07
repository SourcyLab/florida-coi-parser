"""Local-first extraction for ACORD 25 certificate PDFs."""

from .exceptions import (
    CoiParserError,
    DocumentLimitError,
    InvalidPdfError,
    OcrUnavailableError,
    UnsupportedDocumentError,
)
from .models import Coverage, Insurer, ParseResult, Party
from .parser import ParseOptions, parse_acord25, parse_acord25_bytes, parse_acord25_text

__all__ = [
    "CoiParserError",
    "Coverage",
    "DocumentLimitError",
    "Insurer",
    "InvalidPdfError",
    "OcrUnavailableError",
    "ParseOptions",
    "ParseResult",
    "Party",
    "UnsupportedDocumentError",
    "parse_acord25",
    "parse_acord25_bytes",
    "parse_acord25_text",
]

__version__ = "0.1.0"
