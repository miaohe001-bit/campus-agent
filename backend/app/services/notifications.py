from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import ScheduleStatus
from app.db.models import ReminderNotification, Schedule
from app.schemas.notifications import NotificationRead


def sync_schedule_reminders(db: Session, schedule: Schedule) -> None:
    target = schedule.starts_at or schedule.deadline_at
    existing = db.scalars(
        select(ReminderNotification).where(ReminderNotification.schedule_id == schedule.id)
    ).all()
    now = datetime.now(timezone.utc)
    if target is None or schedule.status != ScheduleStatus.pending:
        for notification in existing:
            if notification.status == "pending":
                notification.status = "canceled"
        return

    comparable_target = target if target.tzinfo else target.replace(tzinfo=timezone.utc)
    if comparable_target < now:
        schedule.status = ScheduleStatus.missed
        for notification in existing:
            if notification.status == "pending":
                notification.status = "canceled"
        return

    desired = {
        (minutes, target - timedelta(minutes=minutes))
        for minutes in schedule.reminder_minutes
    }
    existing_keys = {(item.minutes_before, item.remind_at) for item in existing}
    for notification in existing:
        if notification.status == "pending" and (
            notification.minutes_before,
            notification.remind_at,
        ) not in desired:
            notification.status = "canceled"
    for minutes, remind_at in desired - existing_keys:
        db.add(
            ReminderNotification(
                user_id=schedule.user_id,
                schedule_id=schedule.id,
                minutes_before=minutes,
                remind_at=remind_at,
                status="pending",
            )
        )


def sync_user_reminders(db: Session, *, user_id: str) -> None:
    schedules = db.scalars(select(Schedule).where(Schedule.user_id == user_id)).all()
    for schedule in schedules:
        sync_schedule_reminders(db, schedule)
    db.commit()


def list_due_notifications(db: Session, *, user_id: str, limit: int = 20) -> list[NotificationRead]:
    sync_user_reminders(db, user_id=user_id)
    now = datetime.now(timezone.utc)
    notifications = db.scalars(
        select(ReminderNotification)
        .where(ReminderNotification.user_id == user_id)
        .where(ReminderNotification.status == "pending")
        .where(ReminderNotification.remind_at <= now)
        .order_by(ReminderNotification.remind_at.desc())
        .limit(limit)
    ).all()
    result: list[NotificationRead] = []
    for notification in notifications:
        schedule = db.get(Schedule, notification.schedule_id)
        if schedule is None:
            continue
        event_at = schedule.starts_at or schedule.deadline_at
        if event_at is None:
            continue
        result.append(
            NotificationRead(
                id=notification.id,
                schedule_id=schedule.id,
                title=schedule.title,
                schedule_type=schedule.schedule_type.value if hasattr(schedule.schedule_type, "value") else schedule.schedule_type,
                event_at=event_at,
                remind_at=notification.remind_at,
                minutes_before=notification.minutes_before,
                status=notification.status,
            )
        )
    return result


def mark_notification_read(db: Session, *, user_id: str, notification_id: str) -> bool:
    notification = db.scalar(
        select(ReminderNotification)
        .where(ReminderNotification.id == notification_id)
        .where(ReminderNotification.user_id == user_id)
        .where(ReminderNotification.status == "pending")
    )
    if notification is None:
        return False
    notification.status = "read"
    notification.read_at = datetime.now(timezone.utc)
    db.commit()
    return True
