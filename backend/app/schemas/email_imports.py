from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.events import RecruitmentEventRead


class EmailImportCreate(BaseModel):
    provider: str = Field(default="mock", max_length=64)
    message_id: str | None = Field(default=None, max_length=255)
    from_address: str | None = Field(default=None, max_length=255)
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(default="", max_length=20000)
    received_at: datetime | None = None
    application_id: str | None = None
    campaign_id: str | None = None


class EmailImportRead(BaseModel):
    imported: bool
    reason: str | None = None
    event: RecruitmentEventRead | None = None
    parsed: dict[str, Any] = Field(default_factory=dict)


class QQEmailSyncRead(BaseModel):
    ok: bool
    scanned_count: int
    imported_count: int
    skipped_count: int
    reason: str | None = None
    imports: list[EmailImportRead] = Field(default_factory=list)
