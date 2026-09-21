from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.enums import Chamber, ReportType, SourceSystem
from app.db.models.filer import Filer
from app.db.models.filing import Filing
from app.db.models.transaction import Transaction
from app.schemas.filing import FilingListResponse, FilingRead


@dataclass(slots=True)
class FilingFilters:
    limit: int
    offset: int
    chamber: Chamber | None = None
    source_system: SourceSystem | None = None
    member_id: UUID | None = None
    report_type: ReportType | None = None
    start_date: date | None = None
    end_date: date | None = None


class FilingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_filings(self, filters: FilingFilters) -> FilingListResponse:
        transaction_count = func.count(Transaction.id).label("transaction_count")
        statement = (
            select(Filing, Filer, transaction_count)
            .join(Filer, Filing.filer_id == Filer.id)
            .outerjoin(Transaction, Transaction.filing_id == Filing.id)
            .group_by(Filing.id, Filer.id)
        )

        if filters.chamber:
            statement = statement.where(Filing.chamber == filters.chamber)
        if filters.source_system:
            statement = statement.where(Filing.source_system == filters.source_system)
        if filters.member_id:
            statement = statement.where(Filing.filer_id == filters.member_id)
        if filters.report_type:
            statement = statement.where(Filing.report_type == filters.report_type)
        if filters.start_date:
            statement = statement.where(Filing.disclosure_date >= filters.start_date)
        if filters.end_date:
            statement = statement.where(Filing.disclosure_date <= filters.end_date)

        total = self.session.scalar(
            select(func.count()).select_from(statement.order_by(None).subquery())
        ) or 0

        rows = self.session.execute(
            statement.order_by(Filing.disclosure_date.desc().nullslast(), Filing.created_at.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        ).all()

        items = [
            FilingRead(
                id=filing.id,
                member_id=filer.id,
                member_name=filer.normalized_name,
                chamber=filing.chamber,
                source_system=filing.source_system,
                source_filing_id=filing.source_filing_id,
                report_type=filing.report_type,
                report_type_raw=filing.report_type_raw,
                status=filing.status,
                disclosure_date=filing.disclosure_date,
                filed_at=filing.filed_at,
                source_url=filing.source_url,
                document_url=filing.document_url,
                paper_report=filing.paper_report,
                transaction_count=count,
            )
            for filing, filer, count in rows
        ]

        return FilingListResponse(
            items=items,
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

