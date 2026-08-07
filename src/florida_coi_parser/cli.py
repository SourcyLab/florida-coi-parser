"""Command-line entry point for florida-coi-parser."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .exceptions import CoiParserError, OcrUnavailableError
from .parser import ParseOptions, parse_acord25


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="florida-coi-parser",
        description="Extract best-effort structured data from a local ACORD 25 certificate PDF.",
    )
    parser.add_argument("pdf", type=Path, help="Path to a local PDF certificate.")
    parser.add_argument("--output", "-o", type=Path, help="Write JSON to this file instead of stdout.")
    parser.add_argument("--pretty", action="store_true", help="Indent JSON output for readability.")
    parser.add_argument(
        "--include-raw-text",
        action="store_true",
        help="Include the source text in JSON. This can contain sensitive information.",
    )
    parser.add_argument("--ocr", action="store_true", help="Use optional local OCR when no text layer exists.")
    parser.add_argument("--strict", action="store_true", help="Fail unless the document identifies as ACORD 25.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a documented process exit status."""
    args = build_parser().parse_args(argv)
    try:
        result = parse_acord25(
            args.pdf,
            options=ParseOptions(
                include_raw_text=args.include_raw_text,
                enable_ocr=args.ocr,
                strict=args.strict,
            ),
        )
    except OcrUnavailableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except CoiParserError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    rendered = json.dumps(result.to_dict(), indent=2 if args.pretty else None, sort_keys=True) + "\n"
    if args.output:
        try:
            args.output.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            print(f"error: could not write output file: {exc}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
