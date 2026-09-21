from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.db.models.enums import Chamber, RawDocumentType, SourceSystem


@dataclass(slots=True)
class RawArtifactPayload:
    document_type: RawDocumentType
    source_url: str
    content_type: str
    body: bytes
    filename: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceFilingListing:
    source_system: SourceSystem
    chamber: Chamber
    source_filing_id: str
    filer_name: str
    filer_first_name: str | None = None
    filer_last_name: str | None = None
    office_title: str | None = None
    state: str | None = None
    district: str | None = None
    report_type_raw: str = ""
    disclosure_date: date | None = None
    filed_at: datetime | None = None
    source_url: str = ""
    document_url: str | None = None
    filing_year: int | None = None
    paper_report: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DiscoveryBatch:
    listings: list[SourceFilingListing]
    run_artifacts: list[RawArtifactPayload] = field(default_factory=list)


@dataclass(slots=True)
class ParsedTransaction:
    sequence_number: int
    transaction_date_raw: str | None
    disclosure_date_raw: str | None
    owner_raw: str | None
    ticker_raw: str | None
    asset_name_raw: str
    asset_type_raw: str | None
    transaction_type_raw: str
    amount_range_raw: str | None
    comment_raw: str | None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedFilingBundle:
    report_type_raw: str
    filed_at_raw: str | None = None
    transactions: list[ParsedTransaction] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

