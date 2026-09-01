"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("website", sa.String(length=512), nullable=False),
        sa.Column("source_row_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("website"),
    )
    op.create_index(op.f("ix_companies_company_name"), "companies", ["company_name"], unique=False)
    op.create_index(op.f("ix_companies_source_row_id"), "companies", ["source_row_id"], unique=False)

    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("signal_type", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_url", sa.String(length=512), nullable=False),
        sa.Column("extraction_method", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_signals_company_id"), "signals", ["company_id"], unique=False)

    op.create_table(
        "verdicts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("fit", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("follow_up_question", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id"),
    )

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="running", nullable=False),
        sa.Column("companies_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("companies_processed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("companies_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("pipeline_runs")
    op.drop_table("verdicts")
    op.drop_index(op.f("ix_signals_company_id"), table_name="signals")
    op.drop_table("signals")
    op.drop_index(op.f("ix_companies_source_row_id"), table_name="companies")
    op.drop_index(op.f("ix_companies_company_name"), table_name="companies")
    op.drop_table("companies")