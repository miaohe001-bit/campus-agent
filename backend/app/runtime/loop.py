from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.planner.openai_planner import LLMPlanner
from app.schemas.agent import AgentRunRead
from app.services.agent_runs import create_agent_run_record
from app.tools.recruitment import create_planner_todos, read_planner_context


def run_today_agent(
    db: Session,
    *,
    user_id: str,
    plan_date: date,
    available_minutes: int = 60,
) -> AgentRunRead:
    context = read_planner_context(
        db,
        user_id=user_id,
        plan_date=plan_date,
        available_minutes=available_minutes,
    )
    planner = LLMPlanner()
    candidates, planner_trace = planner.plan_today(context)
    decision_trace = {
        **planner_trace,
        "candidate_count": len(candidates),
    }
    created_todos, skipped_todos = create_planner_todos(
        db,
        context=context,
        candidates=candidates,
        decision_trace=decision_trace,
    )
    context_summary = _context_summary(context)
    candidate_dump = [item.model_dump(mode="json") for item in candidates]
    explanation = _explain_run(
        context_summary=context_summary,
        created_count=len(created_todos),
        skipped_count=len(skipped_todos),
        planner=planner_trace["planner"],
    )
    run_record = create_agent_run_record(
        db,
        user_id=user_id,
        run_date=plan_date,
        planner=planner_trace["planner"],
        context_summary=context_summary,
        candidate_todos=candidate_dump,
        created_todo_ids=[todo.id for todo in created_todos],
        skipped_todos=skipped_todos,
        explanation=explanation,
        decision_trace={
            **decision_trace,
            "created_count": len(created_todos),
            "skipped_count": len(skipped_todos),
        },
    )

    return AgentRunRead(
        id=run_record.id,
        user_id=user_id,
        date=plan_date,
        planner=planner_trace["planner"],
        created_count=len(created_todos),
        todos=created_todos,
        explanation=explanation,
        context_summary=context_summary,
        candidate_todos=candidate_dump,
        skipped_todos=skipped_todos,
        decision_trace={
            **decision_trace,
            "created_count": len(created_todos),
            "skipped_count": len(skipped_todos),
        },
    )


def _context_summary(context: Any) -> dict[str, int | bool]:
    return {
        "has_goal": context.goal is not None,
        "campaign_count": len(context.campaigns),
        "application_count": len(context.applications),
        "pending_schedule_count": len(context.schedules),
        "existing_todo_count": len(context.existing_todos),
        "available_minutes": context.available_minutes,
    }


def _explain_run(
    *,
    context_summary: dict[str, int | bool],
    created_count: int,
    skipped_count: int,
    planner: str,
) -> str:
    parts = [
        f"Agent 使用 {planner} Planner，读取到 "
        f"{context_summary['campaign_count']} 个机会、"
        f"{context_summary['application_count']} 个投递、"
        f"{context_summary['pending_schedule_count']} 个待进行日程。"
    ]
    if created_count:
        parts.append(f"这次写入了 {created_count} 条今日待办。")
    if skipped_count:
        parts.append(f"有 {skipped_count} 条候选待办因为今天已存在而跳过。")
    if not created_count and not skipped_count:
        parts.append("这次没有生成新的待办。")
    return "".join(parts)
