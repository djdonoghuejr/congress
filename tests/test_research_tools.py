from __future__ import annotations

import json

import pytest

from app.db.models.enums import Chamber, FilingStatus, OwnerType, ReportType, SourceSystem, TransactionType
from app.db.models.filer import Filer
from app.db.models.filing import Filing
from app.db.models.transaction import Transaction
from app.normalization.common import build_identity_key
from app.research.tools import FilingResearchTools, TradeResearchTools


def _seed_records(db_session):
    filer = Filer(
        identity_key=build_identity_key("senate", "Jane Doe", "NY", None, "Senator"),
        chamber=Chamber.SENATE,
        source_system=SourceSystem.SENATE_EFD,
        raw_name="Jane Doe",
        normalized_name="Jane Doe",
        first_name="Jane",
        last_name="Doe",
        office_title="Senator",
        state="NY",
        district=None,
        source_metadata={},
    )
    db_session.add(filer)
    db_session.flush()
    filing = Filing(
        filer_id=filer.id,
        chamber=Chamber.SENATE,
        source_system=SourceSystem.SENATE_EFD,
        source_filing_id="research-fixture",
        filing_year=2026,
        report_type=ReportType.PERIODIC_TRANSACTION,
        report_type_raw="Periodic Transaction Report",
        status=FilingStatus.PARSED,
        source_url="https://example.com/filing",
        document_url="https://example.com/document",
        paper_report=False,
        raw_metadata={},
    )
    db_session.add(filing)
    db_session.flush()
    db_session.add(
        Transaction(
            filing_id=filing.id,
            filer_id=filer.id,
            chamber=Chamber.SENATE,
            source_system=SourceSystem.SENATE_EFD,
            sequence_number=1,
            owner_raw="Self",
            owner_type=OwnerType.SELF,
            ticker_raw="AAPL",
            ticker="AAPL",
            asset_name_raw="Apple Inc",
            asset_name_normalized="Apple Inc",
            asset_type_raw="Stock",
            asset_type_normalized="Stock",
            transaction_type_raw="Purchase",
            transaction_type=TransactionType.PURCHASE,
            amount_range_raw="$1,001 - $15,000",
            amount_low=1001,
            amount_high=15000,
            source_url="https://example.com/filing",
            raw_payload={},
        )
    )
    db_session.commit()


def test_trade_tool_applies_filters_and_returns_sources(db_session) -> None:
    _seed_records(db_session)
    tool = TradeResearchTools(db_session)

    result = tool.search_trades(ticker="aapl", transaction_type="purchase", limit=1)
    payload = json.loads(result)

    assert payload["total"] == 1
    assert payload["items"][0]["ticker"] == "AAPL"
    assert payload["items"][0]["filing_source_url"] == "https://example.com/filing"


def test_filing_tool_validates_dates_and_limits(db_session) -> None:
    tool = FilingResearchTools(db_session)

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        tool.search_filings(start_date="2026/01/01")
    with pytest.raises(ValueError, match="between 1 and 25"):
        tool.search_filings(limit=26)


def test_filing_tool_can_filter_status(db_session) -> None:
    _seed_records(db_session)
    tool = FilingResearchTools(db_session)

    result = tool.search_filings(status="parsed", limit=5)
    assert json.loads(result)["total"] == 1
