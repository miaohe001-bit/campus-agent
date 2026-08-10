from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.db.enums import ScheduleStatus, ScheduleType


class ScheduleCreate(BaseModel):
    application_id: str | None = None
    campaign_id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    schedule_type: ScheduleType
    status: ScheduleStatus = ScheduleStatus.pending
    starts_at: datetime | None = None
    deadline_at: datetime | None = None
    source: str = Field(default="manual", max_length=64)
    reminder_minutes: list[int] | None = None


class ScheduleUpdate(BaseModel):
    application_id: str | None = None
    campaign_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    schedule_type: ScheduleType | None = None
    status: ScheduleStatus | None = None
    starts_at: datetime | None = None
    deadline_at: datetime | None = None
    source: str | None = Field(default=None, max_length=64)
    reminder_minutes: list[int] | None = None


class ScheduleRead(BaseModel):
    id: str
    user_id: str
    application_id: str | None
    campaign_id: str | None
    title: str
    schedule_type: ScheduleType
    status: ScheduleStatus
    starts_at: datetime | None
    deadline_at: datetime | None
    source: str
    reminder_minutes: list[int]
    change_log: list[dict[str, Any]]

    model_config = {"from_attributes": True}
