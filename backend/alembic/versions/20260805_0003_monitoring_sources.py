"""add monitoring sources and leads

Revision ID: 20260805_0003
Revises: 20260804_0002
Create Date: 2026-08-05
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260805_0003"
down_revision: str | None = "20260804_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "monitoring_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("check_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_type", "value", name="uq_monitoring_source_value"),
    )
    op.create_index(op.f("ix_monitoring_sources_source_type"), "monitoring_sources", ["source_type"], unique=False)
    op.create_index(op.f("ix_monitoring_sources_user_id"), "monitoring_sources", ["user_id"], unique=False)

    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_count", sa.Integer(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["monitoring_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crawl_runs_source_id"), "crawl_runs", ["source_id"], unique=False)
    op.create_index(op.f("ix_crawl_runs_user_id"), "crawl_runs", ["user_id"], unique=False)

    op.create_table(
        "leads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("crawl_run_id", sa.String(length=36), nullable=True),
        sa.Column("source_item_key", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("mentioned_companies", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["crawl_run_id"], ["crawl_runs.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["monitoring_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_item_key", name="uq_lead_source_item_key"),
    )
    op.create_index(op.f("ix_leads_crawl_run_id"), "leads", ["crawl_run_id"], unique=False)
    op.create_index(op.f("ix_leads_source_id"), "leads", ["source_id"], unique=False)
    op.create_index(op.f("ix_leads_user_id"), "leads", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_leads_user_id"), table_name="leads")
    op.drop_index(op.f("ix_leads_source_id"), table_name="leads")
    op.drop_index(op.f("ix_leads_crawl_run_id"), table_name="leads")
    op.drop_table("leads")
    op.drop_index(op.f("ix_crawl_runs_user_id"), table_name="crawl_runs")
    op.drop_index(op.f("ix_crawl_runs_source_id"), table_name="crawl_runs")
    op.drop_table("crawl_runs")
    op.drop_index(op.f("ix_monitoring_sources_user_id"), table_name="monitoring_sources")
    op.drop_index(op.f("ix_monitoring_sources_source_type"), table_name="monitoring_sources")
    op.drop_table("monitoring_sources")
