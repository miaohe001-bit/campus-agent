from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import AgentRun
from app.schemas.agent import AgentRunHistoryRead


def create_agent_run_record(
    db: Session,
    *,
    user_id: str,
    run_date: date,
    planner: str,
    context_summary: dict,
    candidate_todos: list[dict],
    created_todo_ids: list[str],
    skipped_todos: list[dict],
    explanation: str,
    decision_trace: dict,
) -> AgentRunHistoryRead:
    run = AgentRun(
        user_id=user_id,
        run_date=run_date,
        planner=planner,
        status="completed",
        context_summary=context_summary,
        candidate_todos=candidate_todos,
        created_todo_ids=created_todo_ids,
        skipped_todos=skipped_todos,
        explanation=explanation,
        decision_trace=decision_trace,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return AgentRunHistoryRead.model_validate(run)


def list_agent_runs(
    db: Session,
    *,
    user_id: str,
    limit: int = 10,
    offset: int = 0,
) -> list[AgentRunHistoryRead]:
    statement: Select[tuple[AgentRun]] = (
        select(AgentRun)
        .where(AgentRun.user_id == user_id)
        .order_by(AgentRun.created_at.desc())
    )
    runs = db.scalars(statement.limit(limit).offset(offset)).all()
    return [AgentRunHistoryRead.model_validate(run) for run in runs]
