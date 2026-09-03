from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.db.session import SessionLocal
from app.runtime.loop import run_today_agent
from app.services.email_imports import sync_qq_email
from app.services.email_credentials import list_email_credential_user_ids
from app.services.monitoring_pipeline import run_monitoring_pipeline
from app.services.notifications import sync_user_reminders

TODAY_AGENT_JOB_ID = "daily_today_agent"
QQ_EMAIL_SYNC_JOB_ID = "qq_email_sync"
MONITORING_PIPELINE_JOB_ID = "monitoring_pipeline"
REMINDER_SYNC_JOB_ID = "reminder_sync"

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler

    if not settings.scheduler_enabled:
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)
    scheduler.add_job(
        _run_scheduled_reminder_sync,
        IntervalTrigger(minutes=5, timezone=settings.scheduler_timezone),
        id=REMINDER_SYNC_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _run_scheduled_today_agent,
        CronTrigger(
            hour=settings.scheduler_daily_hour,
            minute=settings.scheduler_daily_minute,
            timezone=settings.scheduler_timezone,
        ),
        id=TODAY_AGENT_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    if settings.qq_email_sync_enabled:
        scheduler.add_job(
            _run_scheduled_qq_email_sync,
            IntervalTrigger(
                hours=settings.qq_email_sync_interval_hours,
                timezone=settings.scheduler_timezone,
            ),
            id=QQ_EMAIL_SYNC_JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    if settings.monitoring_pipeline_enabled:
        scheduler.add_job(
            _run_scheduled_monitoring_pipeline,
            IntervalTrigger(
                hours=settings.monitoring_pipeline_interval_hours,
                timezone=settings.scheduler_timezone,
            ),
            id=MONITORING_PIPELINE_JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def shutdown_scheduler() -> None:
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


def scheduler_status() -> dict:
    if not settings.scheduler_enabled:
        return {
            "enabled": False,
            "running": False,
            "jobs": [],
        }

    today_agent_job = _scheduler.get_job(TODAY_AGENT_JOB_ID) if _scheduler else None
    qq_email_sync_job = _scheduler.get_job(QQ_EMAIL_SYNC_JOB_ID) if _scheduler else None
    monitoring_pipeline_job = _scheduler.get_job(MONITORING_PIPELINE_JOB_ID) if _scheduler else None
    reminder_sync_job = _scheduler.get_job(REMINDER_SYNC_JOB_ID) if _scheduler else None
    return {
        "enabled": True,
        "running": bool(_scheduler and _scheduler.running),
        "user_id": settings.scheduler_user_id,
        "timezone": settings.scheduler_timezone,
        "jobs": [
            {
                "id": REMINDER_SYNC_JOB_ID,
                "type": "reminder_sync",
                "enabled": True,
                "interval_minutes": 5,
                "next_run_time": (
                    reminder_sync_job.next_run_time.isoformat()
                    if reminder_sync_job and reminder_sync_job.next_run_time
                    else None
                ),
            },
            {
                "id": TODAY_AGENT_JOB_ID,
                "type": "daily_agent",
                "enabled": True,
                "daily_hour": settings.scheduler_daily_hour,
                "daily_minute": settings.scheduler_daily_minute,
                "next_run_time": (
                    today_agent_job.next_run_time.isoformat()
                    if today_agent_job and today_agent_job.next_run_time
                    else None
                ),
            },
            {
                "id": QQ_EMAIL_SYNC_JOB_ID,
                "type": "qq_email_sync",
                "enabled": settings.qq_email_sync_enabled,
                "interval_hours": settings.qq_email_sync_interval_hours,
                "next_run_time": (
                    qq_email_sync_job.next_run_time.isoformat()
                    if qq_email_sync_job and qq_email_sync_job.next_run_time
                    else None
                ),
            },
            {
                "id": MONITORING_PIPELINE_JOB_ID,
                "type": "monitoring_pipeline",
                "enabled": settings.monitoring_pipeline_enabled,
                "interval_hours": settings.monitoring_pipeline_interval_hours,
                "next_run_time": (
                    monitoring_pipeline_job.next_run_time.isoformat()
                    if monitoring_pipeline_job and monitoring_pipeline_job.next_run_time
                    else None
                ),
            },
        ],
    }


def _run_scheduled_today_agent() -> None:
    db = SessionLocal()
    try:
        run_today_agent(
            db,
            user_id=settings.scheduler_user_id,
            plan_date=date.today(),
        )
    finally:
        db.close()


def _run_scheduled_qq_email_sync() -> None:
    db = SessionLocal()
    try:
        for user_id in list_email_credential_user_ids(db):
            result = sync_qq_email(db, user_id=user_id)
            if result.imported_count > 0:
                run_today_agent(db, user_id=user_id, plan_date=date.today())
    finally:
        db.close()


def _run_scheduled_monitoring_pipeline() -> None:
    db = SessionLocal()
    try:
        run_monitoring_pipeline(
            db,
            user_id=settings.scheduler_user_id,
            plan_date=date.today(),
        )
    finally:
        db.close()


def _run_scheduled_reminder_sync() -> None:
    db = SessionLocal()
    try:
        sync_user_reminders(db, user_id=settings.scheduler_user_id)
    finally:
        db.close()
