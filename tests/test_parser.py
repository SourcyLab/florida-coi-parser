from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from florida_coi_parser import (
    InvalidPdfError,
    ParseOptions,
    UnsupportedDocumentError,
    parse_acord25,
    parse_acord25_text,
)
from florida_coi_parser.cli import main

SAMPLE_TEXT = """
ACORD 25 (2016/03)
CERTIFICATE OF LIABILITY INSURANCE
DATE (MM/DD/YYYY): 06/15/2026
CERTIFICATE NUMBER: CERT-2026-0042
REVISION NUMBER: R1
PRODUCER
Sunshine Agency LLC
100 Main Street
Tampa, FL 33602
PHONE: (813) 555-0100
E-MAIL: certificates@sunshine.example
INSURED
Example Contractor LLC
200 Harbor Avenue
Tampa, FL 33602
INSURERS AFFORDING COVERAGE
INSURER A: Example Mutual Insurance Company NAIC #: 12345
INSURER B: Example Excess Company NAIC #: 54321
COVERAGES
COMMERCIAL GENERAL LIABILITY
ADDL INSRD: Y
SUBR WVD: N
POLICY NUMBER: CGL-100-ABC
POLICY EFF: 01/01/2026
POLICY EXP: 01/01/2027
EACH OCCURRENCE: $1,000,000
GENERAL AGGREGATE: $2,000,000
PRODUCTS - COMP/OP AGG: $2,000,000
AUTOMOBILE LIABILITY
POLICY NUMBER: AUTO-200-ABC
POLICY EFF: 02/01/2026
POLICY EXP: 02/01/2027
COMBINED SINGLE LIMIT: $1,000,000
DESCRIPTION OF OPERATIONS / LOCATIONS / VEHICLES
Certificate issued for the Harbor Buildout project in Tampa, Florida.
CERTIFICATE HOLDER
Example Property Owner, Inc.
300 Bay Street
Tampa, FL 33602
CANCELLATION
SHOULD ANY OF THE ABOVE DESCRIBED POLICIES BE CANCELLED BEFORE THE EXPIRATION DATE THEREOF.
AUTHORIZED REPRESENTATIVE
""".strip()


def make_pdf(path: Path, text: str = SAMPLE_TEXT) -> None:
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    y = 36
    for line in text.splitlines():
        page.insert_text((36, y), line, fontsize=7)
        y += 10
    document.save(path)
    document.close()


def test_parse_text_extracts_core_fields() -> None:
    result = parse_acord25_text(SAMPLE_TEXT)

    assert result.form_type == "acord_25"
    assert result.form_edition == "2016/03"
    assert result.certificate_date == "2026-06-15"
    assert result.certificate_number == "CERT-2026-0042"
    assert result.producer.name == "Sunshine Agency LLC"
    assert result.producer.email == "certificates@sunshine.example"
    assert result.insured.name == "Example Contractor LLC"
    assert result.certificate_holder.name == "Example Property Owner, Inc."
    assert [(insurer.letter, insurer.naic) for insurer in result.insurers] == [("A", "12345"), ("B", "54321")]
    assert len(result.coverages) == 2

    general_liability = result.coverages[0]
    assert general_liability.kind == "commercial_general_liability"
    assert general_liability.policy_number == "CGL-100-ABC"
    assert general_liability.effective_date == "2026-01-01"
    assert general_liability.expiration_date == "2027-01-01"
    assert general_liability.limits["each_occurrence"] == "1000000"
    assert general_liability.limits["general_aggregate"] == "2000000"
    assert general_liability.flags == {"additional_insured": True, "waiver_of_subrogation": False}
    assert result.description_of_operations == "Certificate issued for the Harbor Buildout project in Tampa, Florida."
    assert result.raw_text is None
    assert result.confidence == 1.0


def test_raw_text_is_explicitly_opt_in() -> None:
    result = parse_acord25_text(SAMPLE_TEXT, options=ParseOptions(include_raw_text=True))

    assert result.raw_text == SAMPLE_TEXT
    assert result.coverages[0].raw_text is not None


def test_empty_template_coverage_sections_are_not_reported_as_populated() -> None:
    text = """
    ACORD 25 (2016/03)
    CERTIFICATE OF LIABILITY INSURANCE
    COMMERCIAL GENERAL LIABILITY
    POLICY NUMBER POLICY EFF POLICY EXP
    EACH OCCURRENCE $
    CERTIFICATE HOLDER
    """
    result = parse_acord25_text(text)

    assert result.coverages == []
    assert any("No populated coverage" in warning for warning in result.warnings)


def test_strict_mode_rejects_non_acord_text() -> None:
    with pytest.raises(UnsupportedDocumentError):
        parse_acord25_text("Invoice #123", options=ParseOptions(strict=True))


def test_parse_pdf_and_cli_write_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pdf_path = tmp_path / "synthetic-certificate.pdf"
    output_path = tmp_path / "result.json"
    make_pdf(pdf_path)

    result = parse_acord25(pdf_path)
    assert result.insured.name == "Example Contractor LLC"

    exit_code = main([str(pdf_path), "--pretty", "--output", str(output_path)])
    assert exit_code == 0
    assert capsys.readouterr().out == ""
    parsed_json = json.loads(output_path.read_text(encoding="utf-8"))
    assert parsed_json["certificate_number"] == "CERT-2026-0042"
    assert parsed_json["raw_text"] is None


def test_invalid_pdf_is_rejected() -> None:
    with pytest.raises(InvalidPdfError):
        parse_acord25_bytes = b"not a pdf"
        parse_acord25(parse_acord25_bytes)


def test_blank_template_labels_do_not_create_false_positive_fields() -> None:
    text = """
    ACORD 25 (2016/03)
    CERTIFICATE OF LIABILITY INSURANCE
    PRODUCER CONTACT NAME: PHONE FAX (A/C, No, Ext): E-MAIL ADDRESS:
    INSURED INSURER A: INSURER B:
    COVERAGES CERTIFICATE NUMBER: REVISION NUMBER:
    THIS IS TO CERTIFY THAT THE POLICIES OF INSURANCE LISTED BELOW HAVE BEEN ISSUED.
    COMMERCIAL GENERAL LIABILITY
    POLICY NUMBER (MM/DD/YYYY) POLICY EFF POLICY EXP
    POLICY JECT LOC
    EACH OCCURRENCE $
    DESCRIPTION OF OPERATIONS / LOCATIONS / VEHICLES
    CERTIFICATE HOLDER CANCELLATION
    SHOULD ANY OF THE ABOVE DESCRIBED POLICIES BE CANCELLED.
    """

    result = parse_acord25_text(text)

    assert result.certificate_number is None
    assert result.revision_number is None
    assert result.insured.name is None
    assert result.certificate_holder.name is None
    assert result.coverages == []
    assert result.confidence == 0.4
