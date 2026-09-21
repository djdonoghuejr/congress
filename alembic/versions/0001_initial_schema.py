"""Initial schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-11 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "filers",
        sa.Column("identity_key", sa.String(length=255), nullable=False),
        sa.Column("chamber", sa.Enum("HOUSE", "SENATE", name="chamber_enum", native_enum=False), nullable=False),
        sa.Column(
            "source_system",
            sa.Enum("HOUSE_CLERK", "SENATE_EFD", name="source_system_enum", native_enum=False),
            nullable=False,
        ),
        sa.Column("raw_name", sa.Text(), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("prefix", sa.String(length=32), nullable=True),
        sa.Column("suffix", sa.String(length=32), nullable=True),
        sa.Column("office_title", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=8), nullable=True),
        sa.Column("district", sa.String(length=16), nullable=True),
        sa.Column("source_metadata", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_filers")),
        sa.UniqueConstraint("identity_key", name=op.f("uq_filers_identity_key")),
    )
    op.create_index("ix_filers_normalized_name", "filers", ["normalized_name"], unique=False)

    op.create_table(
        "ingestion_runs",
        sa.Column(
            "source_system",
            sa.Enum("HOUSE_CLERK", "SENATE_EFD", name="source_system_enum", native_enum=False),
            nullable=False,
        ),
        sa.Column("chamber", sa.Enum("HOUSE", "SENATE", name="chamber_enum", native_enum=False), nullable=False),
        sa.Column(
            "status",
            sa.Enum("RUNNING", "SUCCESS", "PARTIAL", "FAILED", name="ingestion_run_status_enum", native_enum=False),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("discovered_count", sa.Integer(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("stored_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_runs")),
    )
    op.create_index("ix_ingestion_runs_started_at", "ingestion_runs", ["started_at"], unique=False)

    op.create_table(
        "ticker_mappings",
        sa.Column("asset_alias", sa.Text(), nullable=False),
        sa.Column("normalized_asset_name", sa.Text(), nullable=False),
        sa.Column("ticker", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ticker_mappings")),
        sa.UniqueConstraint("asset_alias", name=op.f("uq_ticker_mappings_asset_alias")),
    )
    op.create_index("ix_ticker_mappings_alias", "ticker_mappings", ["asset_alias"], unique=False)

    op.create_table(
        "filings",
        sa.Column("filer_id", sa.Uuid(), nullable=False),
        sa.Column("chamber", sa.Enum("HOUSE", "SENATE", name="chamber_enum", native_enum=False), nullable=False),
        sa.Column(
            "source_system",
            sa.Enum("HOUSE_CLERK", "SENATE_EFD", name="source_system_enum", native_enum=False),
            nullable=False,
        ),
        sa.Column("source_filing_id", sa.String(length=255), nullable=False),
        sa.Column("filing_year", sa.Integer(), nullable=True),
        sa.Column(
            "report_type",
            sa.Enum(
                "PERIODIC_TRANSACTION",
                "ANNUAL",
                "CANDIDATE",
                "NEW_FILER",
                "TERMINATION",
                "AMENDMENT",
                "OTHER",
                name="report_type_enum",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("report_type_raw", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DISCOVERED", "PARSED", "PARTIAL", "FAILED", name="filing_status_enum", native_enum=False),
            nullable=False,
        ),
        sa.Column("disclosure_date", sa.Date(), nullable=True),
        sa.Column("filed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("document_url", sa.Text(), nullable=True),
        sa.Column("paper_report", sa.Boolean(), nullable=False),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["filer_id"], ["filers.id"], name=op.f("fk_filings_filer_id_filers")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_filings")),
        sa.UniqueConstraint("source_system", "source_filing_id", name="uq_filings_source_system_source_filing_id"),
    )
    op.create_index("ix_filings_disclosure_date", "filings", ["disclosure_date"], unique=False)
    op.create_index("ix_filings_filer_id", "filings", ["filer_id"], unique=False)

    op.create_table(
        "raw_documents",
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=True),
        sa.Column("filing_id", sa.Uuid(), nullable=True),
        sa.Column(
            "source_system",
            sa.Enum("HOUSE_CLERK", "SENATE_EFD", name="source_system_enum", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "document_type",
            sa.Enum(
                "DISCOVERY_HTML",
                "DISCOVERY_JSON",
                "DISCOVERY_ZIP",
                "INDEX_XML",
                "REPORT_HTML",
                "REPORT_PDF",
                "PAPER_IMAGE",
                name="raw_document_type_enum",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("document_metadata", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["filing_id"],
            ["filings.id"],
            name=op.f("fk_raw_documents_filing_id_filings"),
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_raw_documents_ingestion_run_id_ingestion_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raw_documents")),
    )
    op.create_index("ix_raw_documents_filing_id", "raw_documents", ["filing_id"], unique=False)
    op.create_index(
        "ix_raw_documents_ingestion_run_id",
        "raw_documents",
        ["ingestion_run_id"],
        unique=False,
    )

    op.create_table(
        "transactions",
        sa.Column("filing_id", sa.Uuid(), nullable=False),
        sa.Column("filer_id", sa.Uuid(), nullable=False),
        sa.Column("chamber", sa.Enum("HOUSE", "SENATE", name="chamber_enum", native_enum=False), nullable=False),
        sa.Column(
            "source_system",
            sa.Enum("HOUSE_CLERK", "SENATE_EFD", name="source_system_enum", native_enum=False),
            nullable=False,
        ),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("owner_raw", sa.String(length=255), nullable=True),
        sa.Column(
            "owner_type",
            sa.Enum(
                "SELF",
                "SPOUSE",
                "JOINT",
                "DEPENDENT",
                "OTHER",
                "UNKNOWN",
                name="owner_type_enum",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("ticker_raw", sa.String(length=64), nullable=True),
        sa.Column("ticker", sa.String(length=64), nullable=True),
        sa.Column("asset_name_raw", sa.Text(), nullable=False),
        sa.Column("asset_name_normalized", sa.Text(), nullable=False),
        sa.Column("asset_type_raw", sa.String(length=255), nullable=True),
        sa.Column("asset_type_normalized", sa.String(length=255), nullable=True),
        sa.Column("transaction_type_raw", sa.String(length=255), nullable=False),
        sa.Column(
            "transaction_type",
            sa.Enum(
                "PURCHASE",
                "SALE",
                "EXCHANGE",
                "RECEIPT",
                "OTHER",
                name="transaction_type_enum",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column("disclosure_date", sa.Date(), nullable=True),
        sa.Column("amount_range_raw", sa.String(length=255), nullable=True),
        sa.Column("amount_low", sa.BigInteger(), nullable=True),
        sa.Column("amount_high", sa.BigInteger(), nullable=True),
        sa.Column("comment_raw", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["filing_id"], ["filings.id"], name=op.f("fk_transactions_filing_id_filings")),
        sa.ForeignKeyConstraint(["filer_id"], ["filers.id"], name=op.f("fk_transactions_filer_id_filers")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions")),
        sa.UniqueConstraint("filing_id", "sequence_number", name="uq_transactions_filing_id_sequence_number"),
    )
    op.create_index("ix_transactions_filer_id", "transactions", ["filer_id"], unique=False)
    op.create_index("ix_transactions_ticker", "transactions", ["ticker"], unique=False)
    op.create_index("ix_transactions_transaction_date", "transactions", ["transaction_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transactions_transaction_date", table_name="transactions")
    op.drop_index("ix_transactions_ticker", table_name="transactions")
    op.drop_index("ix_transactions_filer_id", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index("ix_raw_documents_ingestion_run_id", table_name="raw_documents")
    op.drop_index("ix_raw_documents_filing_id", table_name="raw_documents")
    op.drop_table("raw_documents")

    op.drop_index("ix_filings_filer_id", table_name="filings")
    op.drop_index("ix_filings_disclosure_date", table_name="filings")
    op.drop_table("filings")

    op.drop_index("ix_ticker_mappings_alias", table_name="ticker_mappings")
    op.drop_table("ticker_mappings")

    op.drop_index("ix_ingestion_runs_started_at", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")

    op.drop_index("ix_filers_normalized_name", table_name="filers")
    op.drop_table("filers")
