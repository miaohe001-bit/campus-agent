from datetime import date

from sqlalchemy.orm import Session

from app.db.enums import ScheduleStatus, TodoSource, TodoStatus
from app.schemas.agent import PlannerContext, PlannerTodoCandidate
from app.schemas.todos import TodoCreate, TodoRead
from app.services.applications import list_applications
from app.services.campaigns import list_campaigns
from app.services.goals import get_goal
from app.services.schedules import list_schedules
from app.services.todos import create_todo, list_todos


def read_planner_context(
    db: Session,
    *,
    user_id: str,
    plan_date: date,
    available_minutes: int = 60,
) -> PlannerContext:
    goal = get_goal(db, user_id)
    campaigns = list_campaigns(db, include_closed=False, limit=20)
    applications = list_applications(db, user_id=user_id, limit=20)
    schedules = list_schedules(db, user_id=user_id, status=ScheduleStatus.pending, limit=20)
    existing_todos = list_todos(db, user_id=user_id, todo_date=plan_date, limit=20)

    return PlannerContext(
        user_id=user_id,
        date=plan_date,
        available_minutes=available_minutes,
        goal=goal.model_dump(mode="json") if goal else None,
        campaigns=[item.model_dump(mode="json") for item in campaigns],
        applications=[item.model_dump(mode="json") for item in applications],
        schedules=[item.model_dump(mode="json") for item in schedules],
        existing_todos=[item.model_dump(mode="json") for item in existing_todos],
    )


def create_planner_todos(
    db: Session,
    *,
    context: PlannerContext,
    candidates: list[PlannerTodoCandidate],
    decision_trace: dict,
) -> tuple[list[TodoRead], list[dict]]:
    existing_titles = {
        item["title"]
        for item in context.existing_todos
        if item.get("source") == TodoSource.planner and item.get("status") == TodoStatus.pending
    }
    created: list[TodoRead] = []
    skipped: list[dict] = []
    planned_minutes = 0

    for priority_order, candidate in enumerate(candidates[:3], start=1):
        if candidate.title in existing_titles:
            skipped.append({
                "title": candidate.title,
                "reason": "same pending planner todo already exists for this date",
            })
            continue

        candidate_minutes = candidate.estimated_minutes or 15
        if planned_minutes + candidate_minutes > context.available_minutes:
            skipped.append({
                "title": candidate.title,
                "reason": "预计总耗时超过今日可投入时间",
            })
            continue

        payload = TodoCreate(
            date=context.date,
            title=candidate.title,
            source=TodoSource.planner,
            estimated_minutes=candidate.estimated_minutes,
            priority_order=priority_order,
            business_reason=candidate.business_reason,
            decision_trace=decision_trace,
            application_id=candidate.application_id,
            campaign_id=candidate.campaign_id,
        )
        created.append(create_todo(db, user_id=context.user_id, payload=payload))
        existing_titles.add(candidate.title)
        planned_minutes += candidate_minutes

    return created, skipped
