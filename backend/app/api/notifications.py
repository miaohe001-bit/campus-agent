from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.responses import ApiResponse
from app.services.notifications import list_due_notifications, mark_notification_read


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=ApiResponse)
def read_notifications(
    user_id: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse:
    items = list_due_notifications(db, user_id=user_id, limit=limit)
    return ApiResponse(data={"items": [item.model_dump(mode="json") for item in items]})


@router.patch("/{notification_id}/read", response_model=ApiResponse)
def read_notification(
    notification_id: str,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    if not mark_notification_read(db, user_id=user_id, notification_id=notification_id):
        raise HTTPException(status_code=404, detail="notification not found")
    return ApiResponse(data={"read": True})
