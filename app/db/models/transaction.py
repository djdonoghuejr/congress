from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import BigInteger, Date, Enum as SQLEnum, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import Chamber, OwnerType, SourceSystem, TransactionType


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("filing_id", "sequence_number"),
        Index("ix_transactions_ticker", "ticker"),
        Index("ix_transactions_transaction_date", "transaction_date"),
        Index("ix_transactions_filer_id", "filer_id"),
    )

    filing_id: Mapped[UUID] = mapped_column(ForeignKey("filings.id"), nullable=False)
    filer_id: Mapped[UUID] = mapped_column(ForeignKey("filers.id"), nullable=False)
    chamber: Mapped[Chamber] = mapped_column(
        SQLEnum(Chamber, name="chamber_enum", native_enum=False),
        nullable=False,
    )
    source_system: Mapped[SourceSystem] = mapped_column(
        SQLEnum(SourceSystem, name="source_system_enum", native_enum=False),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(nullable=False)
    owner_raw: Mapped[str | None] = mapped_column(String(255))
    owner_type: Mapped[OwnerType] = mapped_column(
        SQLEnum(OwnerType, name="owner_type_enum", native_enum=False),
        nullable=False,
        default=OwnerType.UNKNOWN,
    )
    ticker_raw: Mapped[str | None] = mapped_column(String(64))
    ticker: Mapped[str | None] = mapped_column(String(64))
    asset_name_raw: Mapped[str] = mapped_column(Text, nullable=False)
    asset_name_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    asset_type_raw: Mapped[str | None] = mapped_column(String(255))
    asset_type_normalized: Mapped[str | None] = mapped_column(String(255))
    transaction_type_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType, name="transaction_type_enum", native_enum=False),
        nullable=False,
        default=TransactionType.OTHER,
    )
    transaction_date: Mapped[date | None] = mapped_column(Date)
    disclosure_date: Mapped[date | None] = mapped_column(Date)
    amount_range_raw: Mapped[str | None] = mapped_column(String(255))
    amount_low: Mapped[int | None] = mapped_column(BigInteger)
    amount_high: Mapped[int | None] = mapped_column(BigInteger)
    comment_raw: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    filing = relationship("Filing", back_populates="transactions")
    filer = relationship("Filer", back_populates="transactions")
