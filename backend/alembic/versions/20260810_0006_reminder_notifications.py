"""add reminder notifications

Revision ID: 20260810_0006
Revises: 20260810_0005
Create Date: 2026-08-10
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260810_0006"
down_revision: str | None = "20260810_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reminder_notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("schedule_id", sa.String(length=36), nullable=False),
        sa.Column("minutes_before", sa.Integer(), nullable=False),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schedule_id", "minutes_before", "remind_at", name="uq_schedule_reminder_occurrence"),
    )
    op.create_index(op.f("ix_reminder_notifications_user_id"), "reminder_notifications", ["user_id"])
    op.create_index(op.f("ix_reminder_notifications_schedule_id"), "reminder_notifications", ["schedule_id"])
    op.create_index(op.f("ix_reminder_notifications_remind_at"), "reminder_notifications", ["remind_at"])
    op.create_index(op.f("ix_reminder_notifications_status"), "reminder_notifications", ["status"])


def downgrade() -> None:
    op.drop_table("reminder_notifications")
