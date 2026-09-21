from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, Enum as SQLEnum, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import Chamber, FilingStatus, ReportType, SourceSystem


class Filing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "filings"
    __table_args__ = (
        UniqueConstraint("source_system", "source_filing_id"),
        Index("ix_filings_disclosure_date", "disclosure_date"),
        Index("ix_filings_filer_id", "filer_id"),
    )

    filer_id: Mapped[UUID] = mapped_column(ForeignKey("filers.id"), nullable=False)
    chamber: Mapped[Chamber] = mapped_column(
        SQLEnum(Chamber, name="chamber_enum", native_enum=False),
        nullable=False,
    )
    source_system: Mapped[SourceSystem] = mapped_column(
        SQLEnum(SourceSystem, name="source_system_enum", native_enum=False),
        nullable=False,
    )
    source_filing_id: Mapped[str] = mapped_column(String(255), nullable=False)
    filing_year: Mapped[int | None] = mapped_column(nullable=True)
    report_type: Mapped[ReportType] = mapped_column(
        SQLEnum(ReportType, name="report_type_enum", native_enum=False),
        nullable=False,
        default=ReportType.OTHER,
    )
    report_type_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[FilingStatus] = mapped_column(
        SQLEnum(FilingStatus, name="filing_status_enum", native_enum=False),
        nullable=False,
        default=FilingStatus.DISCOVERED,
    )
    disclosure_date: Mapped[date | None] = mapped_column(Date)
    filed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    document_url: Mapped[str | None] = mapped_column(Text)
    paper_report: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    filer = relationship("Filer", back_populates="filings")
    raw_documents = relationship("RawDocument", back_populates="filing", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="filing", cascade="all, delete-orphan")
