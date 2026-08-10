from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.enums import RecruitmentEventType
from app.db.session import get_db
from app.schemas.events import RecruitmentEventCreate
from app.schemas.responses import ApiResponse
from app.services.events import create_event, list_events

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=ApiResponse)
def read_events(
    user_id: str = Query(..., min_length=1),
    application_id: str | None = None,
    event_type: RecruitmentEventType | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse:
    events = list_events(
        db,
        user_id=user_id,
        application_id=application_id,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data={"items": [item.model_dump(mode="json") for item in events]})


@router.post("", response_model=ApiResponse)
def add_event(
    payload: RecruitmentEventCreate,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    event = create_event(db, user_id=user_id, payload=payload)
    return ApiResponse(data=event.model_dump(mode="json"))

