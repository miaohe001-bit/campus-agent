from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.db.enums import RecruitmentEventType


class RecruitmentEventCreate(BaseModel):
    application_id: str | None = None
    campaign_id: str | None = None
    event_type: RecruitmentEventType
    occurred_at: datetime | None = None
    source: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=255)


class RecruitmentEventRead(BaseModel):
    id: str
    user_id: str
    application_id: str | None
    campaign_id: str | None
    event_type: RecruitmentEventType
    occurred_at: datetime
    source: str
    payload: dict[str, Any]
    idempotency_key: str | None

    model_config = {"from_attributes": True}

