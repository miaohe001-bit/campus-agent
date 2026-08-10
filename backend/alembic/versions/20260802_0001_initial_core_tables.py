"""initial core tables

Revision ID: 20260802_0001
Revises:
Create Date: 2026-08-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260802_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("graduation_year", sa.String(length=32), nullable=False),
        sa.Column("target_positions", sa.JSON(), nullable=False),
        sa.Column("target_cities", sa.JSON(), nullable=False),
        sa.Column("target_industries", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"], unique=True)

    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("target_graduation_year", sa.String(length=32), nullable=True),
        sa.Column("position_categories", sa.JSON(), nullable=True),
        sa.Column("cities", sa.JSON(), nullable=True),
        sa.Column("industries", sa.JSON(), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_campaigns_company_name", "campaigns", ["company_name"])

    op.create_table(
        "goal_companies",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("goal_id", sa.String(length=36), sa.ForeignKey("goals.id"), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("goal_id", "company_name", name="uq_goal_company_name"),
    )
    op.create_index("ix_goal_companies_goal_id", "goal_companies", ["goal_id"])

    op.create_table(
        "applications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("position_name", sa.String(length=255), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_applications_campaign_id", "applications", ["campaign_id"])
    op.create_index("ix_applications_company_name", "applications", ["company_name"])
    op.create_index("ix_applications_position_name", "applications", ["position_name"])
    op.create_index("ix_applications_user_id", "applications", ["user_id"])

    op.create_table(
        "recruitment_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=36), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("campaign_id", sa.String(length=36), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_recruitment_events_application_id", "recruitment_events", ["application_id"])
    op.create_index("ix_recruitment_events_campaign_id", "recruitment_events", ["campaign_id"])
    op.create_index("ix_recruitment_events_event_type", "recruitment_events", ["event_type"])
    op.create_index("ix_recruitment_events_user_id", "recruitment_events", ["user_id"])

    op.create_table(
        "schedules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=36), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("campaign_id", sa.String(length=36), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("schedule_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("change_log", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_schedules_application_id", "schedules", ["application_id"])
    op.create_index("ix_schedules_campaign_id", "schedules", ["campaign_id"])
    op.create_index("ix_schedules_schedule_type", "schedules", ["schedule_type"])
    op.create_index("ix_schedules_user_id", "schedules", ["user_id"])

    op.create_table(
        "todos",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("completion_source", sa.String(length=32), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("priority_order", sa.Integer(), nullable=True),
        sa.Column("business_reason", sa.Text(), nullable=True),
        sa.Column("decision_trace", sa.JSON(), nullable=True),
        sa.Column("application_id", sa.String(length=36), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("campaign_id", sa.String(length=36), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_todos_application_id", "todos", ["application_id"])
    op.create_index("ix_todos_campaign_id", "todos", ["campaign_id"])
    op.create_index("ix_todos_date", "todos", ["date"])
    op.create_index("ix_todos_user_id", "todos", ["user_id"])


def downgrade() -> None:
    op.drop_table("todos")
    op.drop_table("schedules")
    op.drop_table("recruitment_events")
    op.drop_table("applications")
    op.drop_table("goal_companies")
    op.drop_table("campaigns")
    op.drop_table("goals")

