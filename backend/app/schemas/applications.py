from datetime import datetime

from pydantic import BaseModel, Field

from app.db.enums import ApplicationStage


class ApplicationCreate(BaseModel):
    campaign_id: str | None = None
    company_name: str = Field(min_length=1, max_length=255)
    position_name: str = Field(min_length=1, max_length=255)
    stage: ApplicationStage = ApplicationStage.submitted
    source: str = Field(default="manual", max_length=32)


class ApplicationUpdate(BaseModel):
    campaign_id: str | None = None
    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    position_name: str | None = Field(default=None, min_length=1, max_length=255)
    stage: ApplicationStage | None = None
    source: str | None = Field(default=None, max_length=32)


class ApplicationRead(BaseModel):
    id: str
    user_id: str
    campaign_id: str | None
    company_name: str
    position_name: str
    stage: ApplicationStage
    source: str
    last_changed_at: datetime

    model_config = {"from_attributes": True}

