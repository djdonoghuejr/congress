from __future__ import annotations

import argparse
from datetime import date

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ingestion.connectors.house import HouseConnector
from app.ingestion.connectors.senate import SenateConnector
from app.ingestion.parsers.house import HouseParser
from app.ingestion.parsers.senate import SenateParser
from app.ingestion.pipeline.raw_store import RawArtifactStore
from app.services.ingestion import IngestionService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Congress disclosure ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    senate = subparsers.add_parser("ingest-senate", help="Ingest Senate PTR filings")
    senate.add_argument("--start-date", required=True, type=date.fromisoformat)
    senate.add_argument("--end-date", required=True, type=date.fromisoformat)
    senate.add_argument("--limit", type=int, default=None)

    house = subparsers.add_parser("ingest-house", help="Ingest House PTR filings")
    house.add_argument("--year", required=True, type=int)
    house.add_argument("--limit", type=int, default=None)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = get_settings()
    raw_store = RawArtifactStore(settings)
    session = SessionLocal()

    connector = None
    try:
        if args.command == "ingest-senate":
            connector = SenateConnector(settings=settings)
            filing_parser = SenateParser()
            kwargs = {
                "start_date": args.start_date,
                "end_date": args.end_date,
                "limit": args.limit,
            }
        else:
            connector = HouseConnector(settings=settings)
            filing_parser = HouseParser()
            kwargs = {"year": args.year, "limit": args.limit}

        service = IngestionService(session, raw_store)
        run = service.ingest(
            connector=connector,
            parser=filing_parser,
            discovery_kwargs=kwargs,
        )
        print(
            f"run={run.id} status={run.status.value} "
            f"discovered={run.discovered_count} processed={run.processed_count} "
            f"transactions={run.stored_count} errors={run.error_count}"
        )
    finally:
        session.close()
        if connector is not None:
            connector.close()


if __name__ == "__main__":
    main()
