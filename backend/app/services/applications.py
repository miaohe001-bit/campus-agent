from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.enums import ApplicationStage, RecruitmentEventType
from app.db.models import Application, Campaign, RecruitmentEvent
from app.schemas.applications import ApplicationCreate, ApplicationRead, ApplicationUpdate


def list_applications(
    db: Session,
    *,
    user_id: str,
    stage: ApplicationStage | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ApplicationRead]:
    statement: Select[tuple[Application]] = (
        select(Application)
        .where(Application.user_id == user_id)
        .where(Application.deleted_at.is_(None))
        .order_by(Application.last_changed_at.desc())
    )

    if stage is not None:
        statement = statement.where(Application.stage == stage)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            Application.company_name.ilike(pattern) | Application.position_name.ilike(pattern)
        )

    applications = db.scalars(statement.limit(limit).offset(offset)).all()
    return [ApplicationRead.model_validate(application) for application in applications]


def get_application(db: Session, *, user_id: str, application_id: str) -> ApplicationRead | None:
    application = _get_active_application(db, user_id=user_id, application_id=application_id)
    if application is None:
        return None
    return ApplicationRead.model_validate(application)


def create_application(
    db: Session,
    *,
    user_id: str,
    payload: ApplicationCreate,
) -> ApplicationRead:
    campaign = db.get(Campaign, payload.campaign_id) if payload.campaign_id else None
    if payload.campaign_id and campaign is None:
        raise ValueError("campaign not found")

    position_name = payload.position_name.strip()
    if payload.campaign_id:
        existing = db.scalar(
            select(Application)
            .where(Application.user_id == user_id)
            .where(Application.campaign_id == payload.campaign_id)
            .where(Application.position_name == position_name)
            .where(Application.deleted_at.is_(None))
        )
        if existing is not None:
            return ApplicationRead.model_validate(existing)

    data = payload.model_dump()
    data["position_name"] = position_name
    if campaign is not None:
        data["company_name"] = campaign.company_name
    application = Application(user_id=user_id, **data)
    db.add(application)
    db.flush()
    db.add(
        RecruitmentEvent(
            user_id=user_id,
            application_id=application.id,
            campaign_id=application.campaign_id,
            event_type=RecruitmentEventType.application_submitted,
            source=application.source,
            payload={"position_name": application.position_name},
            idempotency_key=f"application-created:{application.id}",
        )
    )
    db.commit()
    db.refresh(application)
    return ApplicationRead.model_validate(application)


def update_application(
    db: Session,
    *,
    user_id: str,
    application_id: str,
    payload: ApplicationUpdate,
) -> ApplicationRead | None:
    application = _get_active_application(db, user_id=user_id, application_id=application_id)
    if application is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(application, field, value)

    if update_data:
        application.last_changed_at = datetime.utcnow()

    db.commit()
    db.refresh(application)
    return ApplicationRead.model_validate(application)


def delete_application(db: Session, *, user_id: str, application_id: str) -> bool:
    application = _get_active_application(db, user_id=user_id, application_id=application_id)
    if application is None:
        return False

    now = datetime.utcnow()
    application.deleted_at = now
    application.last_changed_at = now
    db.commit()
    return True


def _get_active_application(
    db: Session,
    *,
    user_id: str,
    application_id: str,
) -> Application | None:
    return db.scalar(
        select(Application)
        .where(Application.id == application_id)
        .where(Application.user_id == user_id)
        .where(Application.deleted_at.is_(None))
    )
