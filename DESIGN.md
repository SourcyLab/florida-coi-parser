# florida-coi-parser: Initial Design

## Purpose

`florida-coi-parser` is a local-first Python library and command-line interface that extracts a **best-effort structured representation** from user-supplied ACORD 25 Certificate of Liability Insurance PDFs. It is intended to reduce manual transcription in Florida insurance and construction workflows; it does not determine coverage, endorsements, certificate authenticity, cancellation status, legal sufficiency, or regulatory compliance.

ACORD identifies ACORD 25 as the Certificate of Liability Insurance. Certificates generally communicate policy information, coverage lines, limits, and insurers, but are not policies and cannot alter policy terms. [1]

## Scope for version 0.1

| Area | Included | Explicitly excluded |
|---|---|---|
| Input | Local PDF file or bytes-like content | URLs, cloud uploads, email access, or background document retention |
| Primary documents | ACORD 25 digital/text-layer PDFs | ACORD form generation, editing, signing, or form distribution |
| Scan support | Optional local OCR when installed by the caller | Hosted OCR or transmission to a third party |
| Output | Typed Python models and JSON | Legal/insurance advice or pass/fail compliance decisions |
| User interface | Python library and JSON CLI | Web dashboard, database, API server, or telemetry |

## Public Python API

```python
from florida_coi_parser import parse_acord25, ParseOptions

result = parse_acord25(
    "certificate.pdf",
    options=ParseOptions(include_raw_text=False, enable_ocr=False),
)

print(result.insured.name)
print(result.coverages[0].policy_number)
print(result.warnings)
```

The package also exposes `parse_acord25_bytes(data, filename="document.pdf", options=...)` for callers that keep documents in memory. Parsed output is represented by standard-library dataclasses and has a deterministic `to_dict()` method that emits JSON-compatible `snake_case` keys.

## Output contract

```json
{
  "form_type": "acord_25",
  "form_edition": "2016/03",
  "certificate_date": "2026-08-07",
  "certificate_number": "CERT-123",
  "revision_number": null,
  "producer": {"name": "Example Agency", "email": "coi@example.test", "phone": null, "fax": null, "address": ["100 Main St", "Tampa, FL 33602"]},
  "insured": {"name": "Example Contractor LLC", "address": ["200 Harbor Ave", "Tampa, FL 33602"]},
  "insurers": [{"letter": "A", "name": "Example Insurance Company", "naic": "12345"}],
  "coverages": [{"kind": "commercial_general_liability", "policy_number": "CGL-123", "effective_date": "2026-01-01", "expiration_date": "2027-01-01", "limits": {"each_occurrence": "1000000", "general_aggregate": "2000000"}, "flags": {"additional_insured": true, "waiver_of_subrogation": false}, "raw_text": null}],
  "description_of_operations": "Project-specific wording...",
  "certificate_holder": {"name": "Example Owner", "address": ["300 Bay St", "Tampa, FL 33602"]},
  "authorized_representative": null,
  "warnings": ["Coverage values are extracted text, not a determination of coverage."],
  "confidence": 0.86,
  "raw_text": null
}
```

All fields are nullable or empty when unavailable. Monetary amounts are returned as normalized decimal strings, not floating-point values. Dates use ISO `YYYY-MM-DD` only when a parsed date is unambiguous; their source string remains in `raw_text` when the caller requests it.

## Extraction pipeline

The parser will use **PyMuPDF** to validate and open PDFs locally. It first extracts layout-preserving text and word positions from each page. A normalization step strips repeated whitespace while retaining logical lines. Anchor-driven extractors then locate certificate headings, contact blocks, insurer rows, coverage sections, policy identifiers, date pairs, limit labels, description text, and certificate-holder text. The implementation will favor evidence-preserving behavior: it will not invent missing field values, and it will keep unrecognized coverage fragments as warnings rather than silently discarding them.

| Stage | Behavior | Failure behavior |
|---|---|---|
| Validate | Verify PDF signature, byte size, and page-count bounds | Raise a typed `InvalidPdfError` or `DocumentLimitError` |
| Identify | Detect ACORD 25 heading/form edition from text | Return `UnsupportedDocumentError` in strict mode; warning otherwise |
| Extract | Obtain local layout text and words | Attempt optional, local OCR only when enabled |
| Parse | Match stable anchors and normalize candidate values | Leave ambiguous values null and emit warnings |
| Score | Score presence of identity, coverage, and holder anchors | Return a bounded `0.0–1.0` confidence value |
| Serialize | Convert typed models to JSON-compatible dictionaries | Never transmit or persist document data |

The parser supports four normalized coverage kinds: `commercial_general_liability`, `automobile_liability`, `umbrella_excess_liability`, and `workers_compensation_employers_liability`. Unknown/partial sections remain in `unparsed_sections` for auditability. The library may recognize familiar form editions but does not assert whether any edition is current or approved in a particular jurisdiction.

## Privacy, security, and licensing guardrails

The parser processes local bytes only and makes no network requests. It has no telemetry, analytics, API key, or cloud storage dependency. The default result omits raw document text; a caller must opt in with `include_raw_text=True`. It will not log document contents. CLI JSON is written to standard output unless an explicit output path is supplied.

ACORD states that users need a license to use ACORD Forms, so the project will not include or create form templates. [1] The repository will use synthetically generated fixtures only and will exclude all user-supplied certificates, extracted text, downloaded forms, and private validation material through `.gitignore`.

> This tool is a data-extraction utility, not an insurance, legal, or compliance system. Coverage and contractual requirements must be evaluated against the relevant policies, endorsements, agreements, and applicable rules by qualified professionals.

## Command-line interface

```bash
florida-coi-parser certificate.pdf --pretty
florida-coi-parser certificate.pdf --output parsed.json
florida-coi-parser certificate.pdf --include-raw-text --pretty
florida-coi-parser certificate.pdf --ocr --pretty
```

The CLI exits with status `0` for a completed parse (including warnings), `2` for invalid arguments, `3` for invalid or unsupported input, and `4` when a requested optional capability such as OCR is unavailable.

## Package layout

```text
src/florida_coi_parser/
  __init__.py       # stable exports and package version
  cli.py            # command-line entry point
  exceptions.py     # typed errors
  models.py         # dataclass output contract
  parser.py         # orchestration and public parse functions
  extractors.py     # anchor-driven field/coverage extraction
  pdf_text.py       # local PDF text/OCR acquisition
  normalize.py      # dates, money, whitespace, and confidence helpers
tests/
  fixtures/         # synthetic generated PDFs only
  test_parser.py
  test_cli.py
```

## References

[1] [ACORD — Certificates of Insurance Frequently Asked Questions](https://www.acord.org/docs/default-source/forms/acordcertificatesfaq)
