from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.enums import ScheduleStatus, ScheduleType
from app.db.session import get_db
from app.schemas.responses import ApiResponse
from app.schemas.schedules import ScheduleCreate, ScheduleUpdate
from app.services.schedules import (
    cancel_schedule,
    create_schedule,
    get_schedule,
    list_schedules,
    update_schedule,
)

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=ApiResponse)
def read_schedules(
    user_id: str = Query(..., min_length=1),
    status: ScheduleStatus | None = None,
    schedule_type: ScheduleType | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse:
    schedules = list_schedules(
        db,
        user_id=user_id,
        status=status,
        schedule_type=schedule_type,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data={"items": [item.model_dump(mode="json") for item in schedules]})


@router.get("/{schedule_id}", response_model=ApiResponse)
def read_schedule(
    schedule_id: str,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    schedule = get_schedule(db, user_id=user_id, schedule_id=schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="schedule not found")
    return ApiResponse(data=schedule.model_dump(mode="json"))


@router.post("", response_model=ApiResponse)
def add_schedule(
    payload: ScheduleCreate,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    schedule = create_schedule(db, user_id=user_id, payload=payload)
    return ApiResponse(data=schedule.model_dump(mode="json"))


@router.patch("/{schedule_id}", response_model=ApiResponse)
def patch_schedule(
    schedule_id: str,
    payload: ScheduleUpdate,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    schedule = update_schedule(db, user_id=user_id, schedule_id=schedule_id, payload=payload)
    if schedule is None:
        raise HTTPException(status_code=404, detail="schedule not found")
    return ApiResponse(data=schedule.model_dump(mode="json"))


@router.delete("/{schedule_id}", response_model=ApiResponse)
def remove_schedule(
    schedule_id: str,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    canceled = cancel_schedule(db, user_id=user_id, schedule_id=schedule_id)
    if not canceled:
        raise HTTPException(status_code=404, detail="schedule not found")
    return ApiResponse(data={"canceled": True})

