from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.enums import Chamber, OwnerType, SourceSystem, TransactionType


class TradeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    member_name: str
    chamber: Chamber
    source_system: SourceSystem
    filing_id: UUID
    filing_source_url: str
    transaction_date: date | None
    disclosure_date: date | None
    ticker: str | None
    ticker_raw: str | None
    asset_name: str
    asset_name_raw: str
    asset_type: str | None
    transaction_type: TransactionType
    transaction_type_raw: str
    amount_range: str | None
    amount_low: int | None
    amount_high: int | None
    owner_type: OwnerType
    owner_raw: str | None
    comment: str | None


class TradeListResponse(BaseModel):
    items: list[TradeRead]
    total: int
    limit: int
    offset: int

