from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.goals import GoalUpsert
from app.schemas.responses import ApiResponse
from app.services.goals import get_goal, upsert_goal

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=ApiResponse)
def read_goal(
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    goal = get_goal(db, user_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="goal not found")
    return ApiResponse(data=goal.model_dump(mode="json"))


@router.patch("", response_model=ApiResponse)
def update_goal(
    payload: GoalUpsert,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    goal = upsert_goal(db, user_id, payload)
    return ApiResponse(data=goal.model_dump(mode="json"))
