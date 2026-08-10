from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.db.models import Campaign, RecruitmentEvent
from app.schemas.campaigns import CampaignCreate, CampaignRead


def list_campaigns(
    db: Session,
    *,
    company_name: str | None = None,
    include_closed: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[CampaignRead]:
    statement: Select[tuple[Campaign]] = select(Campaign).order_by(
        Campaign.published_at.desc().nullslast(),
        Campaign.created_at.desc(),
    )

    if company_name:
        statement = statement.where(Campaign.company_name == company_name)
    if not include_closed:
        statement = statement.where(or_(Campaign.status.is_(None), Campaign.status.in_(["open", "active", "upcoming"])))

    campaigns = db.scalars(statement.limit(limit).offset(offset)).all()
    return [_campaign_read(db, campaign) for campaign in campaigns]


def get_campaign(db: Session, campaign_id: str) -> CampaignRead | None:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        return None
    return _campaign_read(db, campaign)


def create_campaign(db: Session, payload: CampaignCreate) -> CampaignRead:
    campaign = Campaign(**payload.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return _campaign_read(db, campaign)


def _campaign_read(db: Session, campaign: Campaign) -> CampaignRead:
    application_url = None
    events = db.scalars(
        select(RecruitmentEvent)
        .where(RecruitmentEvent.campaign_id == campaign.id)
        .order_by(RecruitmentEvent.occurred_at.desc())
    ).all()
    for event in events:
        candidate = event.payload.get("application_url")
        if isinstance(candidate, str) and candidate.startswith(("https://", "http://")):
            application_url = candidate
            break
    return CampaignRead.model_validate(campaign).model_copy(
        update={"application_url": application_url}
    )
