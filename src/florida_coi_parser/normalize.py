"""Small, dependency-free normalization helpers."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Optional

_DATE_FORMATS = ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d")


def clean_text(value: str) -> str:
    """Collapse horizontal whitespace while preserving the caller's logical lines."""
    return re.sub(r"[\t \xa0]+", " ", value or "").strip()


def clean_lines(lines: Iterable[str]) -> list[str]:
    """Return non-empty normalized lines in source order."""
    return [clean_text(line) for line in lines if clean_text(line)]


def normalize_date(value: str) -> Optional[str]:
    """Normalize unambiguous common certificate date formats to ISO dates."""
    candidate = clean_text(value).replace(" ", "")
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(candidate, date_format).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_money(value: str) -> Optional[str]:
    """Return a money-like value as a non-floating decimal string, if recognizable."""
    candidate = clean_text(value).replace("$", "").replace(",", "")
    match = re.search(r"(?<![\w.-])(\d+(?:\.\d{1,2})?)(?![\w.-])", candidate)
    if not match:
        return None
    number = match.group(1)
    if "." in number:
        number = number.rstrip("0").rstrip(".")
    return number


def looks_like_contact_line(value: str) -> bool:
    """Identify boilerplate/field-label lines that should not be interpreted as names."""
    upper = clean_text(value).upper()
    labels = (
        "PHONE",
        "FAX",
        "E-MAIL",
        "EMAIL",
        "CONTACT",
        "INSURER",
        "NAIC",
        "DATE",
        "CERTIFICATE",
        "COVERAGE",
    )
    return not value or any(label in upper for label in labels)


def confidence_score(*, has_form: bool, has_insured: bool, has_coverage: bool, has_holder: bool) -> float:
    """Score only extraction completeness, never certificate validity."""
    score = 0.15
    score += 0.25 if has_form else 0.0
    score += 0.25 if has_insured else 0.0
    score += 0.25 if has_coverage else 0.0
    score += 0.10 if has_holder else 0.0
    return min(1.0, score)
