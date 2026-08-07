"""Exceptions raised for invalid inputs or unavailable parser capabilities."""


class CoiParserError(Exception):
    """Base class for parser-specific errors."""


class InvalidPdfError(CoiParserError):
    """Raised when bytes cannot be opened as a PDF."""


class DocumentLimitError(CoiParserError):
    """Raised when a document exceeds configured local safety limits."""


class UnsupportedDocumentError(CoiParserError):
    """Raised in strict mode when a document does not look like ACORD 25."""


class OcrUnavailableError(CoiParserError):
    """Raised when local OCR was requested but is unavailable."""
