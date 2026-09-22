from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.config import Settings
from app.db.models.enums import Chamber, IngestionRunStatus, SourceSystem
from app.db.models.filing import Filing
from app.db.models.raw_document import RawDocument
from app.db.models.transaction import Transaction
from app.ingestion.connectors.senate import SenateConnector
from app.ingestion.parsers.senate import SenateParser
from app.ingestion.pipeline.raw_store import RawArtifactStore
from app.services.ingestion import IngestionService


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "senate"


def test_senate_ingestion_persists_transactions(db_session, tmp_path) -> None:
    home_html = (FIXTURE_DIR / "home.html").read_text(encoding="utf-8")
    search_html = (FIXTURE_DIR / "search.html").read_text(encoding="utf-8")
    report_html = (FIXTURE_DIR / "report.html").read_text(encoding="utf-8")
    results_payload = {
        "draw": 1,
        "recordsTotal": 1,
        "recordsFiltered": 1,
        "data": [
            [
                "John",
                "Boozman",
                "Senator",
                '<a href="/search/view/ptr/test-report/" target="_blank">Periodic Transaction Report for 01/13/2026</a>',
                "01/13/2026",
            ]
        ],
        "result": "ok",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/search/home/") and request.method == "GET":
            return httpx.Response(
                200,
                text=home_html,
                headers={"set-cookie": "csrftoken=testtoken; Path=/"},
            )
        if url.endswith("/search/home/") and request.method == "POST":
            return httpx.Response(
                200,
                text=search_html,
                headers={"set-cookie": "sessionid=testsession; Path=/"},
            )
        if url.endswith("/search/") and request.method == "GET":
            return httpx.Response(
                200,
                text=search_html,
                headers={"set-cookie": "csrftoken=testtoken; Path=/"},
            )
        if url.endswith("/search/") and request.method == "POST":
            return httpx.Response(200, text=search_html)
        if url.endswith("/search/report/data/") and request.method == "POST":
            return httpx.Response(200, json=results_payload)
        if url.endswith("/search/view/ptr/test-report/") and request.method == "GET":
            return httpx.Response(200, text=report_html)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    settings = Settings(
        database_url="sqlite://",
        raw_storage_dir=tmp_path / "raw",
        user_agent="test-agent/1.0",
    )
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    connector = SenateConnector(settings=settings, client=client)
    service = IngestionService(db_session, RawArtifactStore(settings))

    run = service.ingest(
        connector=connector,
        parser=SenateParser(),
        discovery_kwargs={
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 1, 31),
            "limit": 1,
        },
    )

    filings = db_session.scalars(select(Filing)).all()
    transactions = db_session.scalars(select(Transaction)).all()
    raw_documents = db_session.scalars(select(RawDocument)).all()

    assert run.status == IngestionRunStatus.SUCCESS
    assert run.source_system == SourceSystem.SENATE_EFD
    assert run.chamber == Chamber.SENATE
    assert run.discovered_count == 1
    assert run.stored_count == 2
    assert len(filings) == 1
    assert len(transactions) == 2
    assert len(raw_documents) == 4
    assert transactions[0].ticker in {"AAPL", "ANET"}

    repeat_run = service.ingest(
        connector=connector,
        parser=SenateParser(),
        discovery_kwargs={
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 1, 31),
            "limit": 1,
        },
        skip_existing_before=date(2026, 2, 1),
    )
    assert repeat_run.skipped_count == 1
    assert repeat_run.processed_count == 0
    assert len(db_session.scalars(select(Transaction)).all()) == 2
    connector.close()
