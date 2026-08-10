from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.runtime.loop import run_today_agent
from app.schemas.email_imports import EmailImportCreate
from app.schemas.responses import ApiResponse
from app.services.email_imports import import_mock_email, sync_qq_email

router = APIRouter(prefix="/email-imports", tags=["email-imports"])


@router.post("/mock", response_model=ApiResponse)
def create_mock_email_import(
    payload: EmailImportCreate,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = import_mock_email(db, user_id=user_id, payload=payload)
    return ApiResponse(data=result.model_dump(mode="json"))


@router.post("/qq/sync", response_model=ApiResponse)
def sync_qq_email_imports(
    user_id: str = Query(..., min_length=1),
    replan: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = sync_qq_email(db, user_id=user_id)
    data = result.model_dump(mode="json")
    if replan and result.imported_count > 0:
        agent_run = run_today_agent(db, user_id=user_id, plan_date=date.today())
        data["agent_run"] = agent_run.model_dump(mode="json")
    return ApiResponse(data=data)
