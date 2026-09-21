from __future__ import annotations

from app.normalization.amounts import parse_amount_range
from app.normalization.disclosures import (
    normalize_owner_type,
    normalize_report_type,
    normalize_transaction_type,
)
from app.db.models.enums import OwnerType, ReportType, SourceSystem, TransactionType


def test_amount_range_parses_closed_range() -> None:
    parsed = parse_amount_range("$1,001 - $15,000")
    assert parsed.low == 1001
    assert parsed.high == 15000


def test_amount_range_parses_open_range() -> None:
    parsed = parse_amount_range("Over $50,000,000")
    assert parsed.low == 50000000
    assert parsed.high is None


def test_disclosure_normalization_maps_expected_values() -> None:
    assert normalize_transaction_type("Purchase") == TransactionType.PURCHASE
    assert normalize_owner_type("Joint") == OwnerType.JOINT
    assert (
        normalize_report_type("Periodic Transaction Report", SourceSystem.SENATE_EFD)
        == ReportType.PERIODIC_TRANSACTION
    )

