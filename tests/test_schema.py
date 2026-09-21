from __future__ import annotations

from sqlalchemy import inspect


def test_schema_contains_core_tables(db_session) -> None:
    inspector = inspect(db_session.bind)
    table_names = set(inspector.get_table_names())
    assert {
        "filers",
        "filings",
        "raw_documents",
        "transactions",
        "ingestion_runs",
        "ticker_mappings",
    }.issubset(table_names)

