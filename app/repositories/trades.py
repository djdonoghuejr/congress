from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.enums import Chamber
from app.db.models.filer import Filer
from app.db.models.filing import Filing
from app.db.models.transaction import Transaction
from app.schemas.trade import TradeListResponse, TradeRead


@dataclass(slots=True)
class TradeFilters:
    limit: int
    offset: int
    chamber: Chamber | None = None
    ticker: str | None = None
    member_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None


class TradeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _base_query(self):
        return (
            select(Transaction, Filer, Filing)
            .join(Filer, Transaction.filer_id == Filer.id)
            .join(Filing, Transaction.filing_id == Filing.id)
        )

    def list_trades(self, filters: TradeFilters) -> TradeListResponse:
        statement = self._base_query()

        if filters.chamber:
            statement = statement.where(Transaction.chamber == filters.chamber)
        if filters.ticker:
            statement = statement.where(func.upper(Transaction.ticker) == filters.ticker)
        if filters.member_id:
            statement = statement.where(Transaction.filer_id == filters.member_id)
        if filters.start_date:
            statement = statement.where(Transaction.transaction_date >= filters.start_date)
        if filters.end_date:
            statement = statement.where(Transaction.transaction_date <= filters.end_date)

        total = self.session.scalar(
            select(func.count()).select_from(statement.order_by(None).subquery())
        ) or 0

        rows = self.session.execute(
            statement.order_by(
                Transaction.disclosure_date.desc().nullslast(),
                Transaction.transaction_date.desc().nullslast(),
                Transaction.sequence_number.desc(),
            )
            .limit(filters.limit)
            .offset(filters.offset)
        ).all()

        items = [
            TradeRead(
                id=transaction.id,
                member_id=filer.id,
                member_name=filer.normalized_name,
                chamber=transaction.chamber,
                source_system=transaction.source_system,
                filing_id=filing.id,
                filing_source_url=filing.source_url,
                transaction_date=transaction.transaction_date,
                disclosure_date=transaction.disclosure_date,
                ticker=transaction.ticker,
                ticker_raw=transaction.ticker_raw,
                asset_name=transaction.asset_name_normalized,
                asset_name_raw=transaction.asset_name_raw,
                asset_type=transaction.asset_type_normalized,
                transaction_type=transaction.transaction_type,
                transaction_type_raw=transaction.transaction_type_raw,
                amount_range=transaction.amount_range_raw,
                amount_low=transaction.amount_low,
                amount_high=transaction.amount_high,
                owner_type=transaction.owner_type,
                owner_raw=transaction.owner_raw,
                comment=transaction.comment_raw,
            )
            for transaction, filer, filing in rows
        ]

        return TradeListResponse(
            items=items,
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

