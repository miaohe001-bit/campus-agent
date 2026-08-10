from datetime import date, datetime

from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    status: str | None = Field(default=None, max_length=64)
    target_graduation_year: str | None = Field(default=None, max_length=32)
    position_categories: list[str] | None = None
    cities: list[str] | None = None
    industries: list[str] | None = None
    published_at: date | None = None
    deadline_at: datetime | None = None
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = None


class CampaignRead(CampaignCreate):
    id: str
    application_url: str | None = None

    model_config = {"from_attributes": True}
