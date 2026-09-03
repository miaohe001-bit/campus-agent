"""add per-user encrypted email credentials

Revision ID: 20260904_0007
Revises: 20260810_0006
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260904_0007"
down_revision: str | None = "20260810_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_credentials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("encrypted_email_address", sa.Text(), nullable=False),
        sa.Column("encrypted_authorization_code", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_credentials_user_id", "email_credentials", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_table("email_credentials")
