from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.runtime.loop import run_today_agent
from app.runtime.scheduler import scheduler_status
from app.schemas.responses import ApiResponse
from app.services.agent_runs import list_agent_runs

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/runs/today", response_model=ApiResponse)
def create_today_agent_run(
    user_id: str = Query(..., min_length=1),
    plan_date: date = Query(default_factory=date.today, alias="date"),
    available_minutes: int = Query(default=60, ge=15, le=720),
    db: Session = Depends(get_db),
) -> ApiResponse:
    run = run_today_agent(
        db,
        user_id=user_id,
        plan_date=plan_date,
        available_minutes=available_minutes,
    )
    return ApiResponse(data=run.model_dump(mode="json"))


@router.get("/runs", response_model=ApiResponse)
def read_agent_runs(
    user_id: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse:
    runs = list_agent_runs(db, user_id=user_id, limit=limit, offset=offset)
    return ApiResponse(data={"items": [item.model_dump(mode="json") for item in runs]})


@router.get("/scheduler", response_model=ApiResponse)
def read_scheduler_status() -> ApiResponse:
    return ApiResponse(data=scheduler_status())
