"""Public orchestration functions for local ACORD 25 extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from .exceptions import UnsupportedDocumentError
from .extractors import (
    extract_coverages,
    extract_form_metadata,
    extract_insurers,
    extract_parties,
    lines_from_text,
)
from .models import ParseResult
from .normalize import confidence_score
from .pdf_text import extract_text, read_pdf_bytes


@dataclass(frozen=True)
class ParseOptions:
    """Options that control local parsing behavior.

    OCR is opt-in because it requires local optional dependencies and can be slower.
    Raw text is opt-in because certificate text can contain sensitive business information.
    """

    include_raw_text: bool = False
    enable_ocr: bool = False
    strict: bool = False


def parse_acord25(source: Union[str, Path, bytes, bytearray], *, options: ParseOptions | None = None) -> ParseResult:
    """Parse a local PDF path or bytes-like object into a best-effort result."""
    data = read_pdf_bytes(source)
    text = extract_text(data, enable_ocr=(options or ParseOptions()).enable_ocr)
    return parse_acord25_text(text, options=options)


def parse_acord25_bytes(data: bytes, *, filename: str = "document.pdf", options: ParseOptions | None = None) -> ParseResult:
    """Parse in-memory PDF bytes without persisting them to disk.

    The ``filename`` argument is retained for caller diagnostics and intentionally does not
    influence parsing. No network request or document retention occurs.
    """
    del filename
    return parse_acord25(data, options=options)


def parse_acord25_text(text: str, *, options: ParseOptions | None = None) -> ParseResult:
    """Parse extracted certificate text; primarily useful for testing and integrations."""
    options = options or ParseOptions()
    lines = lines_from_text(text)
    form_type, edition, certificate_date, certificate_number, revision_number = extract_form_metadata(lines)

    if not form_type and options.strict:
        raise UnsupportedDocumentError("Document does not appear to be an ACORD 25 certificate.")

    producer, insured, certificate_holder, description = extract_parties(lines)
    insurers = extract_insurers(lines)
    coverages = extract_coverages(lines, include_raw_text=options.include_raw_text)

    warnings: list[str] = [
        "Extracted values are best-effort text transcription, not a determination of coverage, "
        "endorsements, authenticity, cancellation, or compliance."
    ]
    if not form_type:
        warnings.append("The expected ACORD 25 identifier was not found; review the document type.")
    if not text.strip():
        warnings.append("No text layer was found. Re-run with OCR enabled for a locally scanned document.")
    if not insured.name:
        warnings.append("No insured party was confidently extracted.")
    if not coverages:
        warnings.append("No populated coverage section was confidently extracted.")
    if not certificate_holder.name:
        warnings.append("No certificate holder was confidently extracted.")

    result = ParseResult(
        form_type=form_type,
        form_edition=edition,
        certificate_date=certificate_date,
        certificate_number=certificate_number,
        revision_number=revision_number,
        producer=producer,
        insured=insured,
        insurers=insurers,
        coverages=coverages,
        description_of_operations=description,
        certificate_holder=certificate_holder,
        warnings=warnings,
        confidence=confidence_score(
            has_form=bool(form_type),
            has_insured=bool(insured.name),
            has_coverage=bool(coverages),
            has_holder=bool(certificate_holder.name),
        ),
        raw_text=text if options.include_raw_text else None,
    )
    return result
