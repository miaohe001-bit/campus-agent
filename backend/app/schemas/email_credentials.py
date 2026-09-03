from datetime import datetime

from pydantic import BaseModel, Field


class EmailCredentialUpsert(BaseModel):
    email_address: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    authorization_code: str = Field(min_length=6, max_length=128)


class EmailCredentialRead(BaseModel):
    configured: bool
    provider: str = "qq"
    masked_email_address: str | None = None
    enabled: bool = False
    last_synced_at: datetime | None = None
