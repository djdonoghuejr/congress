from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models.enums import Chamber, ReportType, SourceSystem
from app.db.session import get_db
from app.repositories.filings import FilingFilters, FilingRepository
from app.schemas.filing import FilingListResponse

router = APIRouter()


@router.get("/filings", response_model=FilingListResponse)
def list_filings(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    chamber: Chamber | None = None,
    source_system: SourceSystem | None = None,
    member_id: UUID | None = None,
    report_type: ReportType | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
) -> FilingListResponse:
    repository = FilingRepository(db)
    filters = FilingFilters(
        limit=limit,
        offset=offset,
        chamber=chamber,
        source_system=source_system,
        member_id=member_id,
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
    )
    return repository.list_filings(filters)
