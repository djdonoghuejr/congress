from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.json import to_jsonable
from app.db.models.enums import FilingStatus, IngestionRunStatus
from app.db.models.filer import Filer
from app.db.models.filing import Filing
from app.db.models.ingestion_run import IngestionRun
from app.db.models.raw_document import RawDocument
from app.db.models.transaction import Transaction
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.contracts import ParsedFilingBundle, ParsedTransaction, RawArtifactPayload, SourceFilingListing
from app.ingestion.parsers.base import BaseParser
from app.ingestion.pipeline.raw_store import RawArtifactStore
from app.normalization.amounts import parse_amount_range
from app.normalization.common import build_identity_key, normalize_name, parse_date, parse_datetime, split_name
from app.normalization.disclosures import (
    normalize_asset_name,
    normalize_asset_type,
    normalize_owner_type,
    normalize_report_type,
    normalize_transaction_type,
)
from app.db.base import utcnow


class IngestionService:
    def __init__(self, session: Session, raw_store: RawArtifactStore) -> None:
        self.session = session
        self.raw_store = raw_store

    def ingest(
        self,
        *,
        connector: BaseConnector,
        parser: BaseParser,
        discovery_kwargs: dict[str, Any],
    ) -> IngestionRun:
        run = IngestionRun(
            source_system=connector.source_system,
            chamber=connector.chamber,
            status=IngestionRunStatus.RUNNING,
            started_at=utcnow(),
            parameters=to_jsonable(discovery_kwargs),
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)

        batch = connector.discover_filings(**discovery_kwargs)
        run.discovered_count = len(batch.listings)
        self._store_artifacts(batch.run_artifacts, connector, ingestion_run=run)
        self.session.commit()

        saw_partial = False
        for listing in batch.listings:
            filing_id = None
            try:
                filer = self._upsert_filer(listing)
                filing = self._upsert_filing(listing, filer)
                filing_id = filing.id
                self.session.commit()

                artifacts = connector.fetch_filing_artifacts(listing)
                self._store_artifacts(artifacts, connector, filing=filing, ingestion_run=run)
                self.session.commit()

                parsed = parser.parse(listing, artifacts)
                stored_transactions = self._persist_transactions(
                    filing=filing,
                    filer=filer,
                    listing=listing,
                    parsed=parsed,
                )
                filing.status = (
                    FilingStatus.PARSED if stored_transactions > 0 else FilingStatus.PARTIAL
                )
                saw_partial = saw_partial or filing.status == FilingStatus.PARTIAL
                run.processed_count += 1
                run.stored_count += stored_transactions
                self.session.commit()
            except Exception as exc:  # noqa: BLE001
                self.session.rollback()
                run = self.session.get(IngestionRun, run.id)
                filing = self.session.scalar(select(Filing).where(Filing.id == filing_id))
                if filing is not None:
                    filing.status = FilingStatus.PARTIAL if listing.paper_report else FilingStatus.FAILED
                    raw_metadata = to_jsonable(filing.raw_metadata)
                    raw_metadata["parse_error"] = str(exc)
                    filing.raw_metadata = raw_metadata
                run.error_count += 1
                run.error_message = str(exc)
                saw_partial = True
                self.session.commit()

        run.completed_at = utcnow()
        if run.error_count and run.processed_count == 0:
            run.status = IngestionRunStatus.FAILED
        elif run.error_count or saw_partial:
            run.status = IngestionRunStatus.PARTIAL
        else:
            run.status = IngestionRunStatus.SUCCESS
        self.session.commit()
        self.session.refresh(run)
        return run

    def _upsert_filer(self, listing: SourceFilingListing) -> Filer:
        normalized_name = normalize_name(listing.filer_name) or "Unknown"
        first_name = normalize_name(listing.filer_first_name)
        last_name = normalize_name(listing.filer_last_name)
        if not first_name or not last_name:
            split_first, split_last = split_name(normalized_name)
            first_name = first_name or split_first
            last_name = last_name or split_last

        identity_key = build_identity_key(
            listing.chamber.value,
            normalized_name,
            listing.state,
            listing.district,
            listing.office_title,
        )
        filer = self.session.scalar(select(Filer).where(Filer.identity_key == identity_key))
        if filer is None:
            filer = Filer(
                identity_key=identity_key,
                chamber=listing.chamber,
                source_system=listing.source_system,
                raw_name=listing.filer_name,
                normalized_name=normalized_name,
                first_name=first_name,
                last_name=last_name,
                office_title=listing.office_title,
                state=listing.state,
                district=listing.district,
                source_metadata=to_jsonable(listing.metadata),
            )
            self.session.add(filer)
        else:
            filer.raw_name = listing.filer_name
            filer.normalized_name = normalized_name
            filer.first_name = first_name or filer.first_name
            filer.last_name = last_name or filer.last_name
            filer.office_title = listing.office_title or filer.office_title
            filer.state = listing.state or filer.state
            filer.district = listing.district or filer.district
            filer.source_metadata = {
                **to_jsonable(filer.source_metadata),
                **to_jsonable(listing.metadata),
            }
        self.session.flush()
        return filer

    def _upsert_filing(self, listing: SourceFilingListing, filer: Filer) -> Filing:
        filing = self.session.scalar(
            select(Filing).where(
                Filing.source_system == listing.source_system,
                Filing.source_filing_id == listing.source_filing_id,
            )
        )
        report_type = normalize_report_type(listing.report_type_raw, listing.source_system)
        if filing is None:
            filing = Filing(
                filer_id=filer.id,
                chamber=listing.chamber,
                source_system=listing.source_system,
                source_filing_id=listing.source_filing_id,
                filing_year=listing.filing_year,
                report_type=report_type,
                report_type_raw=listing.report_type_raw,
                status=FilingStatus.DISCOVERED,
                disclosure_date=listing.disclosure_date,
                filed_at=listing.filed_at,
                source_url=listing.source_url,
                document_url=listing.document_url,
                paper_report=listing.paper_report,
                raw_metadata=to_jsonable(listing.metadata),
            )
            self.session.add(filing)
        else:
            filing.filer_id = filer.id
            filing.report_type = report_type
            filing.report_type_raw = listing.report_type_raw
            filing.filing_year = listing.filing_year
            filing.disclosure_date = listing.disclosure_date or filing.disclosure_date
            filing.filed_at = listing.filed_at or filing.filed_at
            filing.source_url = listing.source_url
            filing.document_url = listing.document_url
            filing.paper_report = listing.paper_report
            filing.raw_metadata = {
                **to_jsonable(filing.raw_metadata),
                **to_jsonable(listing.metadata),
            }
        self.session.flush()
        return filing

    def _store_artifacts(
        self,
        artifacts: list[RawArtifactPayload],
        connector: BaseConnector,
        *,
        filing: Filing | None = None,
        ingestion_run: IngestionRun | None = None,
    ) -> None:
        for artifact in artifacts:
            storage_path, digest = self.raw_store.store(
                artifact,
                source_system=connector.source_system,
                filing_id=filing.id if filing else None,
                ingestion_run_id=ingestion_run.id if ingestion_run else None,
            )
            raw_document = RawDocument(
                ingestion_run_id=ingestion_run.id if ingestion_run else None,
                filing_id=filing.id if filing else None,
                source_system=connector.source_system,
                document_type=artifact.document_type,
                source_url=artifact.source_url,
                content_type=artifact.content_type,
                sha256=digest,
                storage_path=storage_path,
                document_metadata=to_jsonable(artifact.metadata),
            )
            self.session.add(raw_document)

    def _persist_transactions(
        self,
        *,
        filing: Filing,
        filer: Filer,
        listing: SourceFilingListing,
        parsed: ParsedFilingBundle,
    ) -> int:
        filing.report_type = normalize_report_type(parsed.report_type_raw, listing.source_system)
        filing.report_type_raw = parsed.report_type_raw
        filing.filed_at = parse_datetime(parsed.filed_at_raw) or filing.filed_at
        filing.raw_metadata = {**to_jsonable(filing.raw_metadata), **to_jsonable(parsed.metadata)}

        self.session.execute(delete(Transaction).where(Transaction.filing_id == filing.id))

        count = 0
        for record in parsed.transactions:
            transaction = self._build_transaction(filing, filer, listing, record)
            self.session.add(transaction)
            count += 1
        self.session.flush()
        return count

    def _build_transaction(
        self,
        filing: Filing,
        filer: Filer,
        listing: SourceFilingListing,
        record: ParsedTransaction,
    ) -> Transaction:
        amount_range = parse_amount_range(record.amount_range_raw)
        asset_name = normalize_asset_name(record.asset_name_raw) or record.asset_name_raw
        return Transaction(
            filing_id=filing.id,
            filer_id=filer.id,
            chamber=listing.chamber,
            source_system=listing.source_system,
            sequence_number=record.sequence_number,
            owner_raw=record.owner_raw if record.owner_raw not in {"--", ""} else None,
            owner_type=normalize_owner_type(record.owner_raw),
            ticker_raw=record.ticker_raw if record.ticker_raw not in {"--", ""} else None,
            ticker=record.ticker_raw if record.ticker_raw not in {"--", ""} else None,
            asset_name_raw=record.asset_name_raw,
            asset_name_normalized=asset_name,
            asset_type_raw=record.asset_type_raw,
            asset_type_normalized=normalize_asset_type(record.asset_type_raw),
            transaction_type_raw=record.transaction_type_raw,
            transaction_type=normalize_transaction_type(record.transaction_type_raw),
            transaction_date=parse_date(record.transaction_date_raw),
            disclosure_date=parse_date(record.disclosure_date_raw) or listing.disclosure_date,
            amount_range_raw=amount_range.raw,
            amount_low=amount_range.low,
            amount_high=amount_range.high,
            comment_raw=record.comment_raw if record.comment_raw not in {"--", ""} else None,
            source_url=listing.source_url,
            raw_payload=to_jsonable(record.raw_payload),
        )
