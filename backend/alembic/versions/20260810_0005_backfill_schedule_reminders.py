"""backfill default reminders for existing schedules

Revision ID: 20260810_0005
Revises: 20260810_0004
Create Date: 2026-08-10
"""

from typing import Sequence

from alembic import op


revision: str = "20260810_0005"
down_revision: str | None = "20260810_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE schedules
        SET reminder_minutes = CASE
            WHEN schedule_type = 'interview' THEN '[1440, 120]'::json
            WHEN schedule_type = 'written_test' THEN '[1440, 60]'::json
            WHEN schedule_type IN ('application_deadline', 'assessment_deadline', 'offer_response_deadline')
                THEN '[4320, 1440, 0]'::json
            ELSE '[1440]'::json
        END
        WHERE reminder_minutes::jsonb = '[]'::jsonb
        """
    )


def downgrade() -> None:
    pass
