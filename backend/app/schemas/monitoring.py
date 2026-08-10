from datetime import datetime

from pydantic import BaseModel, Field

from app.db.enums import (
    CrawlRunStatus,
    LeadStatus,
    MonitoringSourceStatus,
    MonitoringSourceType,
)


class MonitoringSourceCreate(BaseModel):
    source_type: MonitoringSourceType
    display_name: str = Field(min_length=1, max_length=255)
    value: str = Field(min_length=1)
    status: MonitoringSourceStatus = MonitoringSourceStatus.active
    check_interval_minutes: int | None = Field(default=None, ge=1)
    config: dict = Field(default_factory=dict)


class MonitoringSourceRead(MonitoringSourceCreate):
    id: str
    user_id: str
    last_checked_at: datetime | None

    model_config = {"from_attributes": True}


class XiaohongshuNoteCandidate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1)
    author_name: str | None = Field(default=None, max_length=255)
    published_at: datetime | None = None
    snippet: str | None = None


class XiaohongshuNoteBatch(BaseModel):
    notes: list[XiaohongshuNoteCandidate] = Field(min_length=1, max_length=50)


class CrawlRunRead(BaseModel):
    id: str
    user_id: str
    source_id: str
    status: CrawlRunStatus
    started_at: datetime
    finished_at: datetime | None
    discovered_count: int
    imported_count: int
    error_message: str | None
    metadata_: dict

    model_config = {"from_attributes": True}


class LeadCreate(BaseModel):
    source_id: str
    crawl_run_id: str | None = None
    source_item_key: str = Field(min_length=1, max_length=512)
    title: str = Field(min_length=1, max_length=255)
    url: str | None = None
    author_name: str | None = Field(default=None, max_length=255)
    published_at: datetime | None = None
    snippet: str | None = None
    mentioned_companies: list[str] = Field(default_factory=list)
    status: LeadStatus = LeadStatus.new
    payload: dict = Field(default_factory=dict)


class LeadRead(LeadCreate):
    id: str
    user_id: str

    model_config = {"from_attributes": True}
