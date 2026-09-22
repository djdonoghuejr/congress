"""Track filings skipped during scheduled ingestion.

Revision ID: 0002_add_skipped_count
Revises: 0001_initial_schema
Create Date: 2026-09-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_add_skipped_count"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingestion_runs",
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("ingestion_runs", "skipped_count", server_default=None)


def downgrade() -> None:
    op.drop_column("ingestion_runs", "skipped_count")
