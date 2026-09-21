from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum as SQLEnum, Index, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import Chamber, IngestionRunStatus, SourceSystem


class IngestionRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        Index("ix_ingestion_runs_started_at", "started_at"),
    )

    source_system: Mapped[SourceSystem] = mapped_column(
        SQLEnum(SourceSystem, name="source_system_enum", native_enum=False),
        nullable=False,
    )
    chamber: Mapped[Chamber] = mapped_column(
        SQLEnum(Chamber, name="chamber_enum", native_enum=False),
        nullable=False,
    )
    status: Mapped[IngestionRunStatus] = mapped_column(
        SQLEnum(IngestionRunStatus, name="ingestion_run_status_enum", native_enum=False),
        nullable=False,
        default=IngestionRunStatus.RUNNING,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    discovered_count: Mapped[int] = mapped_column(nullable=False, default=0)
    processed_count: Mapped[int] = mapped_column(nullable=False, default=0)
    stored_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)

    raw_documents = relationship("RawDocument", back_populates="ingestion_run")
