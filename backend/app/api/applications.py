from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.enums import ApplicationStage
from app.db.session import get_db
from app.schemas.applications import ApplicationCreate, ApplicationUpdate
from app.schemas.responses import ApiResponse
from app.services.applications import (
    create_application,
    delete_application,
    get_application,
    list_applications,
    update_application,
)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=ApiResponse)
def read_applications(
    user_id: str = Query(..., min_length=1),
    stage: ApplicationStage | None = None,
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse:
    applications = list_applications(
        db,
        user_id=user_id,
        stage=stage,
        q=q,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data={"items": [item.model_dump(mode="json") for item in applications]})


@router.get("/{application_id}", response_model=ApiResponse)
def read_application(
    application_id: str,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    application = get_application(db, user_id=user_id, application_id=application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="application not found")
    return ApiResponse(data=application.model_dump(mode="json"))


@router.post("", response_model=ApiResponse)
def add_application(
    payload: ApplicationCreate,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        application = create_application(db, user_id=user_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse(data=application.model_dump(mode="json"))


@router.patch("/{application_id}", response_model=ApiResponse)
def patch_application(
    application_id: str,
    payload: ApplicationUpdate,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    application = update_application(
        db,
        user_id=user_id,
        application_id=application_id,
        payload=payload,
    )
    if application is None:
        raise HTTPException(status_code=404, detail="application not found")
    return ApiResponse(data=application.model_dump(mode="json"))


@router.delete("/{application_id}", response_model=ApiResponse)
def remove_application(
    application_id: str,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    deleted = delete_application(db, user_id=user_id, application_id=application_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="application not found")
    return ApiResponse(data={"deleted": True})
