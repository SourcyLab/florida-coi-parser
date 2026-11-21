"""Local-only PDF validation and text acquisition."""

from __future__ import annotations

from pathlib import Path
from typing import Union

try:
    import pymupdf
except ModuleNotFoundError:  # Older PyMuPDF releases use the legacy module name.
    import fitz as pymupdf

from .exceptions import DocumentLimitError, InvalidPdfError, OcrUnavailableError

MAX_BYTES = 25 * 1024 * 1024
MAX_PAGES = 20


def _open_document(data: bytes) -> pymupdf.Document:
    if not data.startswith(b"%PDF"):
        raise InvalidPdfError("Input does not begin with a PDF signature.")
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise InvalidPdfError("Input could not be opened as a PDF.") from exc
    if document.page_count > MAX_PAGES:
        document.close()
        raise DocumentLimitError(f"PDF has {document.page_count} pages; limit is {MAX_PAGES}.")
    return document


def read_pdf_bytes(source: Union[str, Path, bytes, bytearray]) -> bytes:
    """Read a caller-supplied local file or bytes after enforcing a size limit."""
    if isinstance(source, (bytes, bytearray)):
        data = bytes(source)
    else:
        path = Path(source)
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise InvalidPdfError(f"Could not read PDF: {path}") from exc
    if len(data) > MAX_BYTES:
        raise DocumentLimitError(f"PDF is {len(data)} bytes; limit is {MAX_BYTES} bytes.")
    return data


def extract_text(data: bytes, *, enable_ocr: bool = False) -> str:
    """Extract layout-preserving text locally; use OCR only when explicitly requested."""
    document = _open_document(data)
    try:
        pages = [page.get_text("text", sort=True) for page in document]
        text = "\n".join(page for page in pages if page).strip()
        if text or not enable_ocr:
            return text
        return _ocr_document(document)
    finally:
        document.close()


def _ocr_document(document: pymupdf.Document) -> str:
    """Run caller-requested OCR locally, without a cloud service or document persistence."""
    try:
        import pytesseract  # type: ignore[import-not-found]
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError as exc:
        raise OcrUnavailableError(
            'OCR requires a local Tesseract installation and the OCR extra. '
            'From the repository checkout, run pip install -e ".[ocr]".'
        ) from exc

    text_pages: list[str] = []
    for page in document:
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        text_pages.append(pytesseract.image_to_string(image))
    return "\n".join(text_pages).strip()
