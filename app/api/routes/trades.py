from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models.enums import Chamber
from app.db.session import get_db
from app.repositories.trades import TradeFilters, TradeRepository
from app.schemas.trade import TradeListResponse

router = APIRouter()


def _build_trade_filters(
    *,
    limit: int,
    offset: int,
    chamber: Chamber | None = None,
    ticker: str | None = None,
    member_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> TradeFilters:
    return TradeFilters(
        limit=limit,
        offset=offset,
        chamber=chamber,
        ticker=ticker.upper() if ticker else None,
        member_id=member_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/trades", response_model=TradeListResponse)
def list_trades(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    chamber: Chamber | None = None,
    ticker: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
) -> TradeListResponse:
    repository = TradeRepository(db)
    filters = _build_trade_filters(
        limit=limit,
        offset=offset,
        chamber=chamber,
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
    )
    return repository.list_trades(filters)


@router.get("/members/{member_id}/trades", response_model=TradeListResponse)
def list_member_trades(
    member_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
) -> TradeListResponse:
    repository = TradeRepository(db)
    filters = _build_trade_filters(
        limit=limit,
        offset=offset,
        member_id=member_id,
        start_date=start_date,
        end_date=end_date,
    )
    return repository.list_trades(filters)


@router.get("/tickers/{ticker}/trades", response_model=TradeListResponse)
def list_ticker_trades(
    ticker: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    chamber: Chamber | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
) -> TradeListResponse:
    repository = TradeRepository(db)
    filters = _build_trade_filters(
        limit=limit,
        offset=offset,
        chamber=chamber,
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
    )
    return repository.list_trades(filters)

