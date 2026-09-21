from __future__ import annotations

from sqlalchemy import Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TickerMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ticker_mappings"
    __table_args__ = (
        Index("ix_ticker_mappings_alias", "asset_alias"),
    )

    asset_alias: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    normalized_asset_name: Mapped[str] = mapped_column(Text, nullable=False)
    ticker: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str | None] = mapped_column(String(255))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
