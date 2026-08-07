# florida-coi-parser

A local-first Python library and CLI for extracting best-effort structured data from ACORD 25 Certificate of Liability Insurance PDFs.

Every insurance agency and construction company in Florida handles these certificates. This open-source tool reduces manual transcription while keeping documents local and private.

> **Sponsored by [Sourcy](https://sourcyinc.com/)**
>
> Sourcy builds AI and automation tools that eliminate manual data entry in complex industries.

## Important Disclaimers

1. **Not Legal or Insurance Advice:** This is a data-extraction utility. It does not determine coverage, endorsements, certificate authenticity, cancellation status, or regulatory compliance. You must evaluate coverage against actual policies and endorsements using qualified professionals.
2. **ACORD Licensing:** ACORD states that users must be licensed by ACORD to use ACORD Forms. This library parses documents you supply; it does not generate, distribute, or bundle ACORD forms. You are responsible for securing the necessary permissions for the documents you process.
3. **Local First:** This library operates entirely locally. It makes no network requests, includes no telemetry, and does not persist your documents.

## Installation

Install the library from PyPI (or locally):

```bash
pip install florida-coi-parser
```

To enable optional local OCR for scanned certificates, install the `ocr` extra and ensure [Tesseract](https://github.com/tesseract-ocr/tesseract) is installed on your system:

```bash
pip install "florida-coi-parser[ocr]"
```

## Command-Line Usage

Extract a certificate to formatted JSON:

```bash
florida-coi-parser certificate.pdf --pretty
```

Save the output to a file and enable OCR if the text layer is missing:

```bash
florida-coi-parser scanned_certificate.pdf --ocr --output result.json
```

By default, the raw document text is excluded to prevent accidental leakage of sensitive business information. To include it in the JSON output, use `--include-raw-text`.

## Python API

The Python API provides typed dataclasses and deterministic JSON serialization.

```python
from florida_coi_parser import parse_acord25, ParseOptions

# Parse a local file
result = parse_acord25(
    "certificate.pdf",
    options=ParseOptions(include_raw_text=False, enable_ocr=False)
)

# Access typed fields
print(f"Insured: {result.insured.name}")
for coverage in result.coverages:
    print(f"{coverage.kind}: {coverage.policy_number}")
    if "each_occurrence" in coverage.limits:
        print(f"  Occurrence limit: ${coverage.limits['each_occurrence']}")

# Check for extraction warnings (e.g., missing fields)
for warning in result.warnings:
    print(f"Warning: {warning}")

# Export to a JSON-compatible dictionary
data = result.to_dict()
```

If you already hold the document in memory, use `parse_acord25_bytes(data)`.

## Extraction Behavior

The parser uses a conservative, anchor-driven strategy:

* It identifies standard ACORD 25 headings and coverage rows (General Liability, Auto, Umbrella/Excess, Workers' Comp).
* It normalizes unambiguous dates to `YYYY-MM-DD` and limits to plain decimal strings (e.g., `"1000000"`).
* It ignores empty template fields rather than misidentifying labels as policy numbers.
* It calculates a `confidence` score (0.0 to 1.0) based on the presence of recognized sections, not the legal validity of the certificate.

## Development

Clone the repository and install the development dependencies:

```bash
git clone https://github.com/SourcyLabs/florida-coi-parser.git
cd florida-coi-parser
pip install -e ".[dev]"
```

Run the tests and lint checks:

```bash
pytest
ruff check src tests
```

To protect user privacy and respect form intellectual property, the test suite uses only synthetic, generated text fixtures. **Do not commit real certificates or proprietary form templates to this repository.**

## License

MIT License. See `LICENSE` for details.
