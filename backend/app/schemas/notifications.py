from datetime import datetime

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: str
    schedule_id: str
    title: str
    schedule_type: str
    event_at: datetime
    remind_at: datetime
    minutes_before: int
    status: str

