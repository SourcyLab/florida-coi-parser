"""Conservative, anchor-driven extraction routines for ACORD 25 text layers."""

from __future__ import annotations

import re
from typing import Iterable, Optional

from .models import Coverage, Insurer, Party
from .normalize import (
    clean_lines,
    clean_text,
    looks_like_contact_line,
    normalize_date,
    normalize_money,
)

COVERAGE_MARKERS: tuple[tuple[str, str], ...] = (
    ("COMMERCIAL GENERAL LIABILITY", "commercial_general_liability"),
    ("AUTOMOBILE LIABILITY", "automobile_liability"),
    ("UMBRELLA LIAB", "umbrella_excess_liability"),
    ("EXCESS LIAB", "umbrella_excess_liability"),
    ("WORKERS COMPENSATION", "workers_compensation_employers_liability"),
)

SECTION_HEADINGS = (
    "PRODUCER",
    "INSURED",
    "INSURERS AFFORDING COVERAGE",
    "COVERAGES",
    "DESCRIPTION OF OPERATIONS",
    "CERTIFICATE HOLDER",
    "CANCELLATION",
    "AUTHORIZED REPRESENTATIVE",
)

LIMIT_LABELS: tuple[tuple[str, str], ...] = (
    ("EACH OCCURRENCE", "each_occurrence"),
    ("DAMAGE TO RENTED", "damage_to_rented_premises"),
    ("MED EXP", "medical_expense"),
    ("PERSONAL & ADV INJURY", "personal_and_advertising_injury"),
    ("GENERAL AGGREGATE", "general_aggregate"),
    ("PRODUCTS - COMP/OP AGG", "products_completed_operations_aggregate"),
    ("COMBINED SINGLE LIMIT", "combined_single_limit"),
    ("BODILY INJURY (PER PERSON)", "bodily_injury_per_person"),
    ("BODILY INJURY (PER ACCIDENT)", "bodily_injury_per_accident"),
    ("PROPERTY DAMAGE", "property_damage"),
    ("E.L. EACH ACCIDENT", "employers_liability_each_accident"),
    ("E.L. DISEASE - EA EMPLOYEE", "employers_liability_disease_each_employee"),
    ("E.L. DISEASE - POLICY LIMIT", "employers_liability_disease_policy_limit"),
)


def lines_from_text(text: str) -> list[str]:
    """Normalize non-empty input lines while preserving reading order."""
    return clean_lines(text.splitlines())


def _index_of(lines: list[str], marker: str, start: int = 0) -> Optional[int]:
    marker = marker.upper()
    for index in range(start, len(lines)):
        if lines[index].upper().startswith(marker):
            return index
    for index in range(start, len(lines)):
        if marker in lines[index].upper():
            return index
    return None


def _next_heading_index(lines: list[str], start: int, markers: Iterable[str] = SECTION_HEADINGS) -> int:
    upper_markers = tuple(marker.upper() for marker in markers)
    for index in range(start, len(lines)):
        upper = lines[index].upper()
        if any(marker in upper for marker in upper_markers):
            return index
    return len(lines)


def _block_after(lines: list[str], marker: str, *, next_markers: Iterable[str] = SECTION_HEADINGS) -> list[str]:
    start = _index_of(lines, marker)
    if start is None:
        return []
    end = _next_heading_index(lines, start + 1, next_markers)
    return lines[start + 1 : end]


def _is_template_or_boilerplate(value: str) -> bool:
    upper = clean_text(value).upper()
    phrases = (
        "CERTIFICATE IS ISSUED",
        "THIS CERTIFICATE",
        "THIS IS TO CERTIFY",
        "IF SUBROGATION",
        "SHOULD ANY OF THE ABOVE",
        "ACCORDANCE WITH THE POLICY",
        "ADDITIONAL INSURED PROVISIONS",
        "POLICIES OF INSURANCE LISTED",
    )
    headings = (
        "CERTIFICATE",
        "COVERAGES",
        "INSURER",
        "DESCRIPTION OF OPERATIONS",
        "AUTHORIZED REPRESENTATIVE",
        "CANCELLATION",
    )
    return (
        not upper
        or len(upper) > 100
        or upper in headings
        or any(phrase in upper for phrase in phrases)
        or not re.search(r"[A-Z0-9]", upper)
    )


def _value_after_label(lines: list[str], label: str) -> Optional[str]:
    label_pattern = re.escape(label).replace(r"\ ", r"\s+")
    expression = re.compile(rf"\b{label_pattern}\b\s*[:#-]?\s*(.+)$", re.IGNORECASE)
    forbidden = ("CERTIFICATE NUMBER", "REVISION NUMBER", "POLICY EFF", "POLICY EXP", "MM/DD/YYYY")
    for index, line in enumerate(lines):
        match = expression.search(line)
        if match:
            candidate = clean_text(match.group(1))
            if candidate and candidate.upper() != label.upper() and not any(
                item in candidate.upper() for item in forbidden
            ) and not _is_template_or_boilerplate(candidate):
                return candidate
        if line.upper() == label.upper() and index + 1 < len(lines):
            candidate = clean_text(lines[index + 1])
            if not looks_like_contact_line(candidate) and not _is_template_or_boilerplate(candidate):
                return candidate
    return None


def extract_form_metadata(lines: list[str]) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Extract the form identity, edition, certificate date, and certificate identifiers."""
    whole_text = "\n".join(lines)
    form_type = "acord_25" if re.search(r"\bACORD\s*(?:25|0025)\b", whole_text, re.IGNORECASE) else None
    edition_match = re.search(r"ACORD\s*(?:25|0025)\s*\(?\s*(\d{4}/\d{2})\s*\)?", whole_text, re.IGNORECASE)
    form_edition = edition_match.group(1) if edition_match else None

    date_value: Optional[str] = None
    for line in lines[:20]:
        if "DATE" in line.upper():
            match = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})\b", line)
            if match:
                date_value = normalize_date(match.group(1))
                if date_value:
                    break
    certificate_number = _value_after_label(lines, "CERTIFICATE NUMBER")
    revision_number = _value_after_label(lines, "REVISION NUMBER")
    return form_type, form_edition, date_value, certificate_number, revision_number


def _party_from_block(block: list[str]) -> Party:
    """Parse a best-effort party from an adjacent certificate block."""
    party = Party()
    useful = [
        line
        for line in block
        if not looks_like_contact_line(line) and not _is_template_or_boilerplate(line)
    ]
    for line in block:
        email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", line, re.IGNORECASE)
        phone_match = re.search(r"(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}", line)
        fax_match = re.search(r"FAX\s*(?:\([^)]*\))?\s*[:#-]?\s*((?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4})", line, re.IGNORECASE)
        if email_match:
            party.email = email_match.group(0)
        if fax_match:
            party.fax = fax_match.group(1)
        elif phone_match and party.phone is None:
            party.phone = phone_match.group(0)
    if useful:
        party.name = useful[0]
        party.address = useful[1:4]
    return party


def extract_parties(lines: list[str]) -> tuple[Party, Party, Party, Optional[str]]:
    """Extract producer, insured, certificate holder, and operations description."""
    producer = _party_from_block(
        _block_after(lines, "PRODUCER", next_markers=("INSURED", "INSURERS AFFORDING COVERAGE", "COVERAGES"))
    )
    insured = _party_from_block(
        _block_after(lines, "INSURED", next_markers=("INSURERS AFFORDING COVERAGE", "COVERAGES"))
    )
    holder = _party_from_block(
        _block_after(lines, "CERTIFICATE HOLDER", next_markers=("CANCELLATION", "AUTHORIZED REPRESENTATIVE"))
    )
    description = _block_after(lines, "DESCRIPTION OF OPERATIONS", next_markers=("CERTIFICATE HOLDER", "CANCELLATION"))
    return producer, insured, holder, " ".join(description) or None


def extract_insurers(lines: list[str]) -> list[Insurer]:
    """Extract insurer rows with optional NAIC numbers."""
    block = _block_after(lines, "INSURERS AFFORDING COVERAGE", next_markers=("COVERAGES",))
    insurers: list[Insurer] = []
    seen: set[str] = set()
    for line in block:
        match = re.search(r"\bINSURER\s+([A-F])\s*[:.-]?\s*(.*)$", line, re.IGNORECASE)
        if not match:
            continue
        letter, remainder = match.group(1).upper(), clean_text(match.group(2))
        naic_match = re.search(r"(?:NAIC\s*#?\s*[:.-]?\s*)?(\d{4,6})\b", remainder, re.IGNORECASE)
        naic = naic_match.group(1) if naic_match else None
        name = remainder
        if naic_match:
            name = clean_text(remainder[: naic_match.start()])
        name = re.sub(r"\bNAIC\s*#?\s*[:.-]?$", "", name, flags=re.IGNORECASE).strip(" :-")
        if letter not in seen:
            insurers.append(Insurer(letter=letter, name=name or None, naic=naic))
            seen.add(letter)
    return insurers


def _coverage_starts(lines: list[str]) -> list[tuple[int, str]]:
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        upper = line.upper()
        for marker, kind in COVERAGE_MARKERS:
            if marker in upper:
                if starts and starts[-1][0] == index:
                    continue
                starts.append((index, kind))
                break
    return starts


def _find_labeled_date(block: list[str], label: str) -> Optional[str]:
    label_pattern = re.escape(label).replace("\\ ", "\\s+")
    pattern = re.compile(
        label_pattern + r".*?(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    )
    for line in block:
        match = pattern.search(line)
        if match:
            return normalize_date(match.group(1))
    return None


def _find_dates(block: list[str]) -> list[str]:
    dates: list[str] = []
    for line in block:
        for match in re.finditer(r"\b(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})\b", line):
            value = normalize_date(match.group(1))
            if value and value not in dates:
                dates.append(value)
    return dates


def _extract_limit(block: list[str], label: str) -> Optional[str]:
    for index, line in enumerate(block):
        if label in line.upper():
            same_line = normalize_money(line[line.upper().find(label) + len(label) :])
            if same_line:
                return same_line
            for following in block[index + 1 : index + 3]:
                candidate = normalize_money(following)
                if candidate:
                    return candidate
    return None


def _extract_policy_number(block: list[str]) -> Optional[str]:
    labeled = _value_after_label(block, "POLICY NUMBER")
    if labeled and not re.search(r"\b(?:POLICY EFF|POLICY EXP|MM/DD/YYYY)\b", labeled, re.IGNORECASE):
        return labeled.split()[0]
    ignored_header_values = {"POLICY", "NUMBER", "EFF", "EXP", "JECT", "MM/DD/YYYY"}
    for line in block:
        match = re.search(r"\b(?:POLICY(?:\s*(?:NO|NUMBER))?|POLICY#)\s*[:#-]?\s*([A-Z0-9][A-Z0-9./_-]{2,})\b", line, re.IGNORECASE)
        if match:
            candidate = match.group(1)
            if candidate.upper() not in ignored_header_values:
                return candidate
    return None


def _extract_flags(block: list[str]) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    patterns: tuple[tuple[str, str], ...] = (
        ("additional_insured", r"ADDL\.?\s*(?:INSRD|INSURED|INS)\s*[:=-]?\s*([YN])\b"),
        ("waiver_of_subrogation", r"(?:SUBR\s*WVD|WAIVER(?:\s+OF)?\s+SUBROGATION)\s*[:=-]?\s*([YN])\b"),
    )
    text = "\n".join(block)
    for key, pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            flags[key] = match.group(1).upper() == "Y"
    return flags


def extract_coverages(lines: list[str], *, include_raw_text: bool = False) -> list[Coverage]:
    """Extract populated coverage sections while skipping empty template rows."""
    starts = _coverage_starts(lines)
    coverages: list[Coverage] = []
    seen_kinds: set[str] = set()
    for position, (start, kind) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        for stop_marker in ("DESCRIPTION OF OPERATIONS", "CERTIFICATE HOLDER", "CANCELLATION"):
            stop = _index_of(lines, stop_marker, start + 1)
            if stop is not None:
                end = min(end, stop)
        block = lines[start:end]
        dates = _find_dates(block)
        policy_number = _extract_policy_number(block)
        limits = {key: value for label, key in LIMIT_LABELS if (value := _extract_limit(block, label))}
        flags = _extract_flags(block)
        populated = bool(policy_number or dates or limits or flags)
        if not populated or kind in seen_kinds:
            continue
        coverage = Coverage(
            kind=kind,
            policy_number=policy_number,
            effective_date=_find_labeled_date(block, "POLICY EFF") or (dates[0] if dates else None),
            expiration_date=_find_labeled_date(block, "POLICY EXP") or (dates[1] if len(dates) > 1 else None),
            limits=limits,
            flags=flags,
            raw_text="\n".join(block) if include_raw_text else None,
        )
        coverages.append(coverage)
        seen_kinds.add(kind)
    return coverages
