from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.enums import (
    ApplicationStage,
    CompanyPriority,
    CompletionSource,
    CrawlRunStatus,
    LeadStatus,
    MonitoringSourceStatus,
    MonitoringSourceType,
    RecruitmentEventType,
    ScheduleStatus,
    ScheduleType,
    TodoSource,
    TodoStatus,
)


def new_id() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class Goal(Base, TimestampMixin):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    graduation_year: Mapped[str] = mapped_column(String(32))
    target_positions: Mapped[list[str]] = mapped_column(JSON)
    target_cities: Mapped[list[str]] = mapped_column(JSON)
    target_industries: Mapped[list[str]] = mapped_column(JSON)

    companies: Mapped[list["GoalCompany"]] = relationship(
        back_populates="goal",
        cascade="all, delete-orphan",
    )


class GoalCompany(Base, TimestampMixin):
    __tablename__ = "goal_companies"
    __table_args__ = (UniqueConstraint("goal_id", "company_name", name="uq_goal_company_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id"), index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    priority: Mapped[CompanyPriority] = mapped_column(String(32))

    goal: Mapped[Goal] = relationship(back_populates="companies")


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(64))
    target_graduation_year: Mapped[str | None] = mapped_column(String(32))
    position_categories: Mapped[list[str] | None] = mapped_column(JSON)
    cities: Mapped[list[str] | None] = mapped_column(JSON)
    industries: Mapped[list[str] | None] = mapped_column(JSON)
    published_at: Mapped[date | None] = mapped_column(Date)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_name: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"), index=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    position_name: Mapped[str] = mapped_column(String(255), index=True)
    stage: Mapped[ApplicationStage] = mapped_column(String(32), default=ApplicationStage.submitted)
    source: Mapped[str] = mapped_column(String(32), default="manual")
    last_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    campaign: Mapped[Campaign | None] = relationship()


class RecruitmentEvent(Base):
    __tablename__ = "recruitment_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    application_id: Mapped[str | None] = mapped_column(ForeignKey("applications.id"), index=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"), index=True)
    event_type: Mapped[RecruitmentEventType] = mapped_column(String(64), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)

    application: Mapped[Application | None] = relationship()
    campaign: Mapped[Campaign | None] = relationship()


class Schedule(Base, TimestampMixin):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    application_id: Mapped[str | None] = mapped_column(ForeignKey("applications.id"), index=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    schedule_type: Mapped[ScheduleType] = mapped_column(String(64), index=True)
    status: Mapped[ScheduleStatus] = mapped_column(String(32), default=ScheduleStatus.pending)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(64), default="manual")
    reminder_minutes: Mapped[list[int]] = mapped_column(JSON, default=list)
    change_log: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    application: Mapped[Application | None] = relationship()
    campaign: Mapped[Campaign | None] = relationship()


class ReminderNotification(Base, TimestampMixin):
    __tablename__ = "reminder_notifications"
    __table_args__ = (
        UniqueConstraint(
            "schedule_id",
            "minutes_before",
            "remind_at",
            name="uq_schedule_reminder_occurrence",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    schedule_id: Mapped[str] = mapped_column(ForeignKey("schedules.id"), index=True)
    minutes_before: Mapped[int] = mapped_column(Integer)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    schedule: Mapped[Schedule] = relationship()


class Todo(Base, TimestampMixin):
    __tablename__ = "todos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[TodoStatus] = mapped_column(String(32), default=TodoStatus.pending)
    source: Mapped[TodoSource] = mapped_column(String(32), default=TodoSource.planner)
    completion_source: Mapped[CompletionSource | None] = mapped_column(String(32))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_minutes: Mapped[int | None] = mapped_column(Integer)
    priority_order: Mapped[int | None] = mapped_column(Integer)
    business_reason: Mapped[str | None] = mapped_column(Text)
    decision_trace: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    application_id: Mapped[str | None] = mapped_column(ForeignKey("applications.id"), index=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"), index=True)

    application: Mapped[Application | None] = relationship()
    campaign: Mapped[Campaign | None] = relationship()


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    run_date: Mapped[date] = mapped_column(Date, index=True)
    planner: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="completed")
    context_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    candidate_todos: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_todo_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    skipped_todos: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    explanation: Mapped[str | None] = mapped_column(Text)
    decision_trace: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class MonitoringSource(Base, TimestampMixin):
    __tablename__ = "monitoring_sources"
    __table_args__ = (UniqueConstraint("user_id", "source_type", "value", name="uq_monitoring_source_value"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    source_type: Mapped[MonitoringSourceType] = mapped_column(String(64), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(Text)
    status: Mapped[MonitoringSourceStatus] = mapped_column(String(32), default=MonitoringSourceStatus.active)
    check_interval_minutes: Mapped[int | None] = mapped_column(Integer)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class CrawlRun(Base, TimestampMixin):
    __tablename__ = "crawl_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("monitoring_sources.id"), index=True)
    status: Mapped[CrawlRunStatus] = mapped_column(String(32), default=CrawlRunStatus.pending)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    source: Mapped[MonitoringSource] = relationship()


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("user_id", "source_item_key", name="uq_lead_source_item_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("monitoring_sources.id"), index=True)
    crawl_run_id: Mapped[str | None] = mapped_column(ForeignKey("crawl_runs.id"), index=True)
    source_item_key: Mapped[str] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(Text)
    author_name: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snippet: Mapped[str | None] = mapped_column(Text)
    mentioned_companies: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[LeadStatus] = mapped_column(String(32), default=LeadStatus.new)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    source: Mapped[MonitoringSource] = relationship()
    crawl_run: Mapped[CrawlRun | None] = relationship()
