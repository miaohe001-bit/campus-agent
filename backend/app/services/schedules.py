from datetime import datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.enums import ScheduleStatus, ScheduleType
from app.db.models import Schedule
from app.schemas.schedules import ScheduleCreate, ScheduleRead, ScheduleUpdate
from app.services.notifications import sync_schedule_reminders


def list_schedules(
    db: Session,
    *,
    user_id: str,
    status: ScheduleStatus | None = None,
    schedule_type: ScheduleType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ScheduleRead]:
    statement: Select[tuple[Schedule]] = (
        select(Schedule)
        .where(Schedule.user_id == user_id)
        .order_by(
            Schedule.starts_at.asc().nullslast(),
            Schedule.deadline_at.asc().nullslast(),
            Schedule.created_at.desc(),
        )
    )

    if status is not None:
        statement = statement.where(Schedule.status == status)
    if schedule_type is not None:
        statement = statement.where(Schedule.schedule_type == schedule_type)

    schedules = db.scalars(statement.limit(limit).offset(offset)).all()
    return [ScheduleRead.model_validate(schedule) for schedule in schedules]


def get_schedule(db: Session, *, user_id: str, schedule_id: str) -> ScheduleRead | None:
    schedule = _get_schedule(db, user_id=user_id, schedule_id=schedule_id)
    if schedule is None:
        return None
    return ScheduleRead.model_validate(schedule)


def create_schedule(
    db: Session,
    *,
    user_id: str,
    payload: ScheduleCreate,
) -> ScheduleRead:
    data = payload.model_dump()
    if data["reminder_minutes"] is None:
        data["reminder_minutes"] = default_reminder_minutes(payload.schedule_type)
    schedule = Schedule(user_id=user_id, change_log=[], **data)
    db.add(schedule)
    db.flush()
    sync_schedule_reminders(db, schedule)
    db.commit()
    db.refresh(schedule)
    return ScheduleRead.model_validate(schedule)


def update_schedule(
    db: Session,
    *,
    user_id: str,
    schedule_id: str,
    payload: ScheduleUpdate,
) -> ScheduleRead | None:
    schedule = _get_schedule(db, user_id=user_id, schedule_id=schedule_id)
    if schedule is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    if "reminder_minutes" in update_data:
        update_data["reminder_minutes"] = _normalize_reminder_minutes(
            update_data["reminder_minutes"] or []
        )
    if update_data:
        schedule.change_log = [
            *schedule.change_log,
            _change_log_entry(update_data),
        ]
    for field, value in update_data.items():
        setattr(schedule, field, value)

    sync_schedule_reminders(db, schedule)

    db.commit()
    db.refresh(schedule)
    return ScheduleRead.model_validate(schedule)


def cancel_schedule(db: Session, *, user_id: str, schedule_id: str) -> bool:
    schedule = _get_schedule(db, user_id=user_id, schedule_id=schedule_id)
    if schedule is None:
        return False

    schedule.status = ScheduleStatus.canceled
    schedule.change_log = [
        *schedule.change_log,
        _change_log_entry({"status": ScheduleStatus.canceled}),
    ]
    sync_schedule_reminders(db, schedule)
    db.commit()
    return True


def _get_schedule(db: Session, *, user_id: str, schedule_id: str) -> Schedule | None:
    return db.scalar(
        select(Schedule)
        .where(Schedule.id == schedule_id)
        .where(Schedule.user_id == user_id)
    )


def _change_log_entry(changes: dict[str, Any]) -> dict[str, Any]:
    return {
        "changed_at": datetime.utcnow().isoformat(),
        "changes": {
            key: (
                value.isoformat()
                if isinstance(value, datetime)
                else value.value
                if hasattr(value, "value")
                else value
            )
            for key, value in changes.items()
        },
    }


def default_reminder_minutes(schedule_type: ScheduleType) -> list[int]:
    if schedule_type == ScheduleType.interview:
        return [1440, 120]
    if schedule_type == ScheduleType.written_test:
        return [1440, 60]
    if schedule_type in {
        ScheduleType.application_deadline,
        ScheduleType.assessment_deadline,
        ScheduleType.offer_response_deadline,
    }:
        return [4320, 1440, 0]
    return [1440]


def _normalize_reminder_minutes(values: list[int]) -> list[int]:
    return sorted({value for value in values if 0 <= value <= 60 * 24 * 30}, reverse=True)
