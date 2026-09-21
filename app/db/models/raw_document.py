from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import RawDocumentType, SourceSystem


class RawDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "raw_documents"
    __table_args__ = (
        Index("ix_raw_documents_filing_id", "filing_id"),
        Index("ix_raw_documents_ingestion_run_id", "ingestion_run_id"),
    )

    ingestion_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("ingestion_runs.id"))
    filing_id: Mapped[UUID | None] = mapped_column(ForeignKey("filings.id"))
    source_system: Mapped[SourceSystem] = mapped_column(
        SQLEnum(SourceSystem, name="source_system_enum", native_enum=False),
        nullable=False,
    )
    document_type: Mapped[RawDocumentType] = mapped_column(
        SQLEnum(RawDocumentType, name="raw_document_type_enum", native_enum=False),
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    document_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    ingestion_run = relationship("IngestionRun", back_populates="raw_documents")
    filing = relationship("Filing", back_populates="raw_documents")
