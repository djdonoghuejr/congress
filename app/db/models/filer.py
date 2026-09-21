from __future__ import annotations

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import Chamber, SourceSystem


class Filer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "filers"
    __table_args__ = (
        Index("ix_filers_normalized_name", "normalized_name"),
    )

    identity_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    chamber: Mapped[Chamber] = mapped_column(
        SQLEnum(Chamber, name="chamber_enum", native_enum=False),
        nullable=False,
    )
    source_system: Mapped[SourceSystem] = mapped_column(
        SQLEnum(SourceSystem, name="source_system_enum", native_enum=False),
        nullable=False,
    )
    raw_name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    prefix: Mapped[str | None] = mapped_column(String(32))
    suffix: Mapped[str | None] = mapped_column(String(32))
    office_title: Mapped[str | None] = mapped_column(String(255))
    state: Mapped[str | None] = mapped_column(String(8))
    district: Mapped[str | None] = mapped_column(String(16))
    source_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    filings = relationship("Filing", back_populates="filer", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="filer")
