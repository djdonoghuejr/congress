from __future__ import annotations

import json
from datetime import date
from typing import Any

from agents import function_tool
from sqlalchemy.orm import Session

from app.db.models.enums import Chamber, FilingStatus, ReportType, TransactionType
from app.repositories.filings import FilingFilters, FilingRepository
from app.repositories.trades import TradeFilters, TradeRepository

MAX_RESULTS = 25


def _parse_date(value: str | None, field_name: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format") from exc


def _parse_enum(value: str | None, enum_type: type, field_name: str) -> Any:
    if value is None:
        return None
    try:
        return enum_type(value.lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ValueError(f"{field_name} must be one of: {allowed}") from exc


def _limit(value: int) -> int:
    if value < 1 or value > MAX_RESULTS:
        raise ValueError(f"limit must be between 1 and {MAX_RESULTS}")
    return value


class TradeResearchTools:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search_trades(
        self,
        ticker: str | None = None,
        member_name: str | None = None,
        chamber: str | None = None,
        transaction_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 10,
    ) -> str:
        """Search stored congressional trades using bounded, read-only filters."""
        if ticker and len(ticker.strip()) > 32:
            raise ValueError("ticker is too long")
        filters = TradeFilters(
            limit=_limit(limit),
            offset=0,
            chamber=_parse_enum(chamber, Chamber, "chamber"),
            ticker=ticker.strip().upper() if ticker else None,
            member_name=member_name.strip() if member_name else None,
            transaction_type=_parse_enum(transaction_type, TransactionType, "transaction_type"),
            start_date=_parse_date(start_date, "start_date"),
            end_date=_parse_date(end_date, "end_date"),
        )
        if filters.start_date and filters.end_date and filters.start_date > filters.end_date:
            raise ValueError("start_date cannot be after end_date")
        response = TradeRepository(self.session).list_trades(filters)
        return json.dumps(
            {
                "total": response.total,
                "returned": len(response.items),
                "items": [item.model_dump(mode="json") for item in response.items],
            }
        )

def build_trade_tools(session: Session) -> list[Any]:
    return [function_tool(TradeResearchTools(session).search_trades)]


class FilingResearchTools:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search_filings(
        self,
        member_name: str | None = None,
        chamber: str | None = None,
        report_type: str | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 10,
    ) -> str:
        """Search stored congressional filings using bounded, read-only filters."""
        filters = FilingFilters(
            limit=_limit(limit),
            offset=0,
            chamber=_parse_enum(chamber, Chamber, "chamber"),
            member_name=member_name.strip() if member_name else None,
            report_type=_parse_enum(report_type, ReportType, "report_type"),
            status=_parse_enum(status, FilingStatus, "status"),
            start_date=_parse_date(start_date, "start_date"),
            end_date=_parse_date(end_date, "end_date"),
        )
        if filters.start_date and filters.end_date and filters.start_date > filters.end_date:
            raise ValueError("start_date cannot be after end_date")
        response = FilingRepository(self.session).list_filings(filters)
        return json.dumps(
            {
                "total": response.total,
                "returned": len(response.items),
                "items": [item.model_dump(mode="json") for item in response.items],
            }
        )

def build_filing_tools(session: Session) -> list[Any]:
    return [function_tool(FilingResearchTools(session).search_filings)]
