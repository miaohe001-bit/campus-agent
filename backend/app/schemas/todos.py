from datetime import date as dt_date
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.db.enums import CompletionSource, TodoSource, TodoStatus


class TodoCreate(BaseModel):
    date: dt_date
    title: str = Field(min_length=1, max_length=255)
    source: TodoSource = TodoSource.user
    estimated_minutes: int | None = Field(default=None, ge=1)
    priority_order: int | None = Field(default=None, ge=1)
    business_reason: str | None = None
    decision_trace: dict[str, Any] | None = None
    application_id: str | None = None
    campaign_id: str | None = None


class TodoUpdate(BaseModel):
    date: dt_date | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: TodoStatus | None = None
    estimated_minutes: int | None = Field(default=None, ge=1)
    priority_order: int | None = Field(default=None, ge=1)
    business_reason: str | None = None
    decision_trace: dict[str, Any] | None = None
    application_id: str | None = None
    campaign_id: str | None = None


class TodoCompletionUpdate(BaseModel):
    completed: bool
    completion_source: CompletionSource = CompletionSource.user


class TodoRead(BaseModel):
    id: str
    user_id: str
    date: dt_date
    title: str
    status: TodoStatus
    source: TodoSource
    completion_source: CompletionSource | None
    completed_at: datetime | None
    estimated_minutes: int | None
    priority_order: int | None
    business_reason: str | None
    decision_trace: dict[str, Any] | None
    application_id: str | None
    campaign_id: str | None

    model_config = {"from_attributes": True}
