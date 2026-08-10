"""add schedule reminder preferences

Revision ID: 20260810_0004
Revises: 20260805_0003
Create Date: 2026-08-10
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260810_0004"
down_revision: str | None = "20260805_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "schedules",
        sa.Column("reminder_minutes", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("schedules", "reminder_minutes")
