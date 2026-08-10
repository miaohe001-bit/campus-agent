from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.campaigns import CampaignCreate
from app.schemas.responses import ApiResponse
from app.services.campaigns import create_campaign, get_campaign, list_campaigns

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=ApiResponse)
def read_campaigns(
    company_name: str | None = None,
    include_closed: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse:
    campaigns = list_campaigns(
        db,
        company_name=company_name,
        include_closed=include_closed,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data={"items": [item.model_dump(mode="json") for item in campaigns]})


@router.get("/{campaign_id}", response_model=ApiResponse)
def read_campaign(campaign_id: str, db: Session = Depends(get_db)) -> ApiResponse:
    campaign = get_campaign(db, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="campaign not found")
    return ApiResponse(data=campaign.model_dump(mode="json"))


@router.post("", response_model=ApiResponse)
def add_campaign(payload: CampaignCreate, db: Session = Depends(get_db)) -> ApiResponse:
    campaign = create_campaign(db, payload)
    return ApiResponse(data=campaign.model_dump(mode="json"))

