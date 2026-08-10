from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.responses import ApiResponse

router = APIRouter()


@router.get("/health", response_model=ApiResponse)
def health_check() -> ApiResponse:
    return ApiResponse(data={"status": "ok"})


@router.get("/health/db", response_model=ApiResponse)
def database_health_check(db: Session = Depends(get_db)) -> ApiResponse:
    db.execute(text("select 1"))
    return ApiResponse(data={"database": "ok"})
