from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.enums import Chamber, FilingStatus, ReportType, SourceSystem


class FilingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    member_name: str
    chamber: Chamber
    source_system: SourceSystem
    source_filing_id: str
    report_type: ReportType
    report_type_raw: str
    status: FilingStatus
    disclosure_date: date | None
    filed_at: datetime | None
    source_url: str
    document_url: str | None
    paper_report: bool
    transaction_count: int


class FilingListResponse(BaseModel):
    items: list[FilingRead]
    total: int
    limit: int
    offset: int

