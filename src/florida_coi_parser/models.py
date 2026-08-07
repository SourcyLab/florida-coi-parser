"""Typed, JSON-friendly output models for parsed certificates."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Party:
    """A named party and the contact details visible on a certificate."""

    name: Optional[str] = None
    address: List[str] = field(default_factory=list)
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None


@dataclass
class Insurer:
    """An insurer identified in the insurers-affording-coverage table."""

    letter: str
    name: Optional[str] = None
    naic: Optional[str] = None


@dataclass
class Coverage:
    """One coverage section extracted from an ACORD 25 certificate."""

    kind: str
    policy_number: Optional[str] = None
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    limits: Dict[str, str] = field(default_factory=dict)
    flags: Dict[str, bool] = field(default_factory=dict)
    raw_text: Optional[str] = None


@dataclass
class ParseResult:
    """The best-effort structured result returned by the public parser API."""

    form_type: Optional[str] = None
    form_edition: Optional[str] = None
    certificate_date: Optional[str] = None
    certificate_number: Optional[str] = None
    revision_number: Optional[str] = None
    producer: Party = field(default_factory=Party)
    insured: Party = field(default_factory=Party)
    insurers: List[Insurer] = field(default_factory=list)
    coverages: List[Coverage] = field(default_factory=list)
    description_of_operations: Optional[str] = None
    certificate_holder: Party = field(default_factory=Party)
    authorized_representative: Optional[str] = None
    unparsed_sections: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: float = 0.0
    raw_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a deterministic dictionary suitable for JSON serialization."""
        data = asdict(self)
        data["confidence"] = round(max(0.0, min(1.0, self.confidence)), 2)
        return data
