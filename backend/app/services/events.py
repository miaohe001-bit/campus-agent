from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.enums import ApplicationStage, RecruitmentEventType, ScheduleStatus, ScheduleType, TodoStatus
from app.db.models import Application, RecruitmentEvent, Schedule, Todo
from app.schemas.events import RecruitmentEventCreate, RecruitmentEventRead
from app.services.schedules import default_reminder_minutes
from app.services.notifications import sync_schedule_reminders

EVENT_STAGE_UPDATES = {
    RecruitmentEventType.application_submitted: ApplicationStage.submitted,
    RecruitmentEventType.assessment_received: ApplicationStage.assessment,
    RecruitmentEventType.assessment_completed: ApplicationStage.assessment,
    RecruitmentEventType.written_test_scheduled: ApplicationStage.written_test,
    RecruitmentEventType.interview_scheduled: ApplicationStage.interview_1,
    RecruitmentEventType.offer_received: ApplicationStage.offer,
    RecruitmentEventType.rejected: ApplicationStage.failed,
}

EVENT_SCHEDULE_TYPES = {
    RecruitmentEventType.assessment_received: ScheduleType.assessment_deadline,
    RecruitmentEventType.written_test_scheduled: ScheduleType.written_test,
    RecruitmentEventType.interview_scheduled: ScheduleType.interview,
    RecruitmentEventType.interview_rescheduled: ScheduleType.interview,
    RecruitmentEventType.deadline_updated: ScheduleType.application_deadline,
    RecruitmentEventType.offer_received: ScheduleType.offer_response_deadline,
}


def list_events(
    db: Session,
    *,
    user_id: str,
    application_id: str | None = None,
    event_type: RecruitmentEventType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[RecruitmentEventRead]:
    statement: Select[tuple[RecruitmentEvent]] = (
        select(RecruitmentEvent)
        .where(RecruitmentEvent.user_id == user_id)
        .order_by(RecruitmentEvent.occurred_at.desc())
    )

    if application_id is not None:
        statement = statement.where(RecruitmentEvent.application_id == application_id)
    if event_type is not None:
        statement = statement.where(RecruitmentEvent.event_type == event_type)

    events = db.scalars(statement.limit(limit).offset(offset)).all()
    return [RecruitmentEventRead.model_validate(event) for event in events]


def create_event(
    db: Session,
    *,
    user_id: str,
    payload: RecruitmentEventCreate,
) -> RecruitmentEventRead:
    if payload.idempotency_key:
        existing = db.scalar(
            select(RecruitmentEvent).where(
                RecruitmentEvent.idempotency_key == payload.idempotency_key
            )
        )
        if existing is not None:
            return RecruitmentEventRead.model_validate(existing)

    event = RecruitmentEvent(
        user_id=user_id,
        occurred_at=payload.occurred_at or datetime.utcnow(),
        **payload.model_dump(exclude={"occurred_at"}),
    )
    db.add(event)
    db.flush()
    _apply_deterministic_updates(db, event)
    db.commit()
    db.refresh(event)
    return RecruitmentEventRead.model_validate(event)


def _apply_deterministic_updates(db: Session, event: RecruitmentEvent) -> None:
    _apply_application_stage_update(db, event)
    _apply_schedule_update(db, event)
    _apply_todo_update(db, event)


def _apply_application_stage_update(db: Session, event: RecruitmentEvent) -> None:
    if event.application_id is None:
        return

    next_stage = EVENT_STAGE_UPDATES.get(event.event_type)
    if next_stage is None:
        return

    application = db.get(Application, event.application_id)
    if application is None or application.user_id != event.user_id or application.deleted_at is not None:
        return

    application.stage = next_stage
    application.last_changed_at = event.occurred_at


def _apply_schedule_update(db: Session, event: RecruitmentEvent) -> None:
    if event.event_type == RecruitmentEventType.interview_canceled:
        _cancel_related_pending_schedules(db, event, ScheduleType.interview)
        return

    schedule_type = EVENT_SCHEDULE_TYPES.get(event.event_type)
    if schedule_type is None:
        return

    schedule_time = _extract_schedule_time(event)
    if schedule_time is None:
        return

    existing_schedule = _find_related_pending_schedule(db, event, schedule_type)
    if existing_schedule is None:
        schedule = Schedule(
                user_id=event.user_id,
                application_id=event.application_id,
                campaign_id=event.campaign_id,
                title=_schedule_title(event, schedule_type),
                schedule_type=schedule_type,
                status=ScheduleStatus.pending,
                starts_at=schedule_time if schedule_type in {ScheduleType.written_test, ScheduleType.interview} else None,
                deadline_at=schedule_time if schedule_type not in {ScheduleType.written_test, ScheduleType.interview} else None,
                source=event.source,
                reminder_minutes=default_reminder_minutes(schedule_type),
                change_log=[
                    {
                        "changed_at": event.occurred_at.isoformat(),
                        "changes": {"created_from_event_id": event.id},
                    }
                ],
            )
        db.add(schedule)
        db.flush()
        sync_schedule_reminders(db, schedule)
        return

    previous_time = existing_schedule.starts_at or existing_schedule.deadline_at
    if schedule_type in {ScheduleType.written_test, ScheduleType.interview}:
        existing_schedule.starts_at = schedule_time
    else:
        existing_schedule.deadline_at = schedule_time
    existing_schedule.status = ScheduleStatus.pending
    existing_schedule.change_log = [
        *existing_schedule.change_log,
        {
            "changed_at": event.occurred_at.isoformat(),
            "changes": {
                "updated_from_event_id": event.id,
                "previous_time": previous_time.isoformat() if previous_time else None,
                "new_time": schedule_time.isoformat(),
            },
        },
    ]
    sync_schedule_reminders(db, existing_schedule)


def _extract_schedule_time(event: RecruitmentEvent) -> datetime | None:
    raw_value = event.payload.get("scheduled_at") or event.payload.get("deadline_at")
    if raw_value is None:
        return None
    if isinstance(raw_value, datetime):
        return raw_value
    if isinstance(raw_value, str):
        try:
            return datetime.fromisoformat(raw_value)
        except ValueError:
            return None
    return None


def _find_related_pending_schedule(
    db: Session,
    event: RecruitmentEvent,
    schedule_type: ScheduleType,
) -> Schedule | None:
    statement = (
        select(Schedule)
        .where(Schedule.user_id == event.user_id)
        .where(Schedule.schedule_type == schedule_type)
        .where(Schedule.status == ScheduleStatus.pending)
    )
    if event.application_id is not None:
        statement = statement.where(Schedule.application_id == event.application_id)
    if event.campaign_id is not None:
        statement = statement.where(Schedule.campaign_id == event.campaign_id)
    return db.scalar(statement.order_by(Schedule.created_at.desc()))


def _cancel_related_pending_schedules(
    db: Session,
    event: RecruitmentEvent,
    schedule_type: ScheduleType,
) -> None:
    schedule = _find_related_pending_schedule(db, event, schedule_type)
    if schedule is None:
        return
    schedule.status = ScheduleStatus.canceled
    schedule.change_log = [
        *schedule.change_log,
        {
            "changed_at": event.occurred_at.isoformat(),
            "changes": {"canceled_from_event_id": event.id},
        },
    ]
    sync_schedule_reminders(db, schedule)


def _schedule_title(event: RecruitmentEvent, schedule_type: ScheduleType) -> str:
    title = event.payload.get("title")
    if isinstance(title, str) and title:
        return title
    return schedule_type.value


def _apply_todo_update(db: Session, event: RecruitmentEvent) -> None:
    if event.event_type != RecruitmentEventType.rejected or event.application_id is None:
        return

    todos = db.scalars(
        select(Todo)
        .where(Todo.user_id == event.user_id)
        .where(Todo.application_id == event.application_id)
        .where(Todo.status == TodoStatus.pending)
    ).all()

    for todo in todos:
        todo.status = TodoStatus.expired
        todo.business_reason = _append_business_reason(
            todo.business_reason,
            f"Expired because recruitment event {event.id} rejected the related application.",
        )


def _append_business_reason(current: str | None, addition: str) -> str:
    if not current:
        return addition
    return f"{current}\n{addition}"
