from __future__ import annotations

from app.db.base import utcnow
from app.db.models.enums import Chamber, FilingStatus, OwnerType, ReportType, SourceSystem, TransactionType
from app.db.models.filer import Filer
from app.db.models.filing import Filing
from app.db.models.transaction import Transaction
from app.normalization.common import build_identity_key


def test_trade_and_filing_endpoints_return_stored_data(api_client, db_session) -> None:
    filer = Filer(
        identity_key=build_identity_key("senate", "John Boozman", "AR", None, "Senator"),
        chamber=Chamber.SENATE,
        source_system=SourceSystem.SENATE_EFD,
        raw_name="John Boozman",
        normalized_name="John Boozman",
        first_name="John",
        last_name="Boozman",
        office_title="Senator",
        state="AR",
        district=None,
        source_metadata={},
    )
    db_session.add(filer)
    db_session.flush()

    filing = Filing(
        filer_id=filer.id,
        chamber=Chamber.SENATE,
        source_system=SourceSystem.SENATE_EFD,
        source_filing_id="fixture-report",
        filing_year=2026,
        report_type=ReportType.PERIODIC_TRANSACTION,
        report_type_raw="Periodic Transaction Report",
        status=FilingStatus.PARSED,
        disclosure_date=utcnow().date(),
        source_url="https://efdsearch.senate.gov/search/view/ptr/fixture-report/",
        document_url="https://efdsearch.senate.gov/search/view/ptr/fixture-report/",
        paper_report=False,
        raw_metadata={},
    )
    db_session.add(filing)
    db_session.flush()

    transaction = Transaction(
        filing_id=filing.id,
        filer_id=filer.id,
        chamber=Chamber.SENATE,
        source_system=SourceSystem.SENATE_EFD,
        sequence_number=1,
        owner_raw="Joint",
        owner_type=OwnerType.JOINT,
        ticker_raw="AAPL",
        ticker="AAPL",
        asset_name_raw="Apple Inc",
        asset_name_normalized="Apple Inc",
        asset_type_raw="Stock",
        asset_type_normalized="Stock",
        transaction_type_raw="Purchase",
        transaction_type=TransactionType.PURCHASE,
        transaction_date=utcnow().date(),
        disclosure_date=utcnow().date(),
        amount_range_raw="$1,001 - $15,000",
        amount_low=1001,
        amount_high=15000,
        comment_raw=None,
        source_url=filing.source_url,
        raw_payload={},
    )
    db_session.add(transaction)
    db_session.commit()

    trades_response = api_client.get("/trades")
    member_response = api_client.get(f"/members/{filer.id}/trades")
    ticker_response = api_client.get("/tickers/AAPL/trades")
    filings_response = api_client.get("/filings")

    assert trades_response.status_code == 200
    assert trades_response.json()["total"] == 1
    assert trades_response.json()["items"][0]["ticker"] == "AAPL"

    assert member_response.status_code == 200
    assert member_response.json()["items"][0]["member_name"] == "John Boozman"

    assert ticker_response.status_code == 200
    assert ticker_response.json()["items"][0]["asset_name"] == "Apple Inc"

    assert filings_response.status_code == 200
    assert filings_response.json()["items"][0]["source_filing_id"] == "fixture-report"
