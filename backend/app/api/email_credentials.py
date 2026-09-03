from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.email_credentials import EmailCredentialUpsert
from app.schemas.responses import ApiResponse
from app.services.email_credentials import (
    delete_email_credential,
    get_email_credential_status,
    upsert_email_credential,
)


router = APIRouter(prefix="/email-credentials", tags=["email-credentials"])


@router.get("", response_model=ApiResponse)
def read_email_credential_status(
    user_id: str = Query(..., min_length=1), db: Session = Depends(get_db)
) -> ApiResponse:
    result = get_email_credential_status(db, user_id=user_id)
    return ApiResponse(data=result.model_dump(mode="json"))


@router.put("", response_model=ApiResponse)
def configure_email_credential(
    payload: EmailCredentialUpsert,
    user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        result = upsert_email_credential(db, user_id=user_id, payload=payload)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return ApiResponse(data=result.model_dump(mode="json"))


@router.delete("", response_model=ApiResponse)
def remove_email_credential(
    user_id: str = Query(..., min_length=1), db: Session = Depends(get_db)
) -> ApiResponse:
    return ApiResponse(data={"deleted": delete_email_credential(db, user_id=user_id)})
