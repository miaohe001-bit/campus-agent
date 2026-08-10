from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.todos import TodoRead


class PlannerTodoCandidate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    estimated_minutes: int | None = Field(default=None, ge=1)
    business_reason: str | None = None
    application_id: str | None = None
    campaign_id: str | None = None


class RecruitmentArticleDecision(BaseModel):
    is_official_recruitment: bool = False
    confidence: str = Field(default="low", pattern="^(low|medium|high)$")
    company_name: str | None = None
    graduation_year: str | None = None
    campaign_name: str | None = None
    position_categories: list[str] | None = None
    cities: list[str] | None = None
    deadline_at: str | None = None
    published_at: str | None = None
    application_url: str | None = None
    reason: str | None = None


class PlannerContext(BaseModel):
    user_id: str
    date: date
    available_minutes: int = Field(default=60, ge=15, le=720)
    goal: dict[str, Any] | None
    campaigns: list[dict[str, Any]]
    applications: list[dict[str, Any]]
    schedules: list[dict[str, Any]]
    existing_todos: list[dict[str, Any]]


class AgentRunRead(BaseModel):
    id: str | None = None
    user_id: str
    date: date
    planner: str
    created_count: int
    todos: list[TodoRead]
    explanation: str | None = None
    context_summary: dict[str, Any] = Field(default_factory=dict)
    candidate_todos: list[dict[str, Any]] = Field(default_factory=list)
    skipped_todos: list[dict[str, Any]] = Field(default_factory=list)
    decision_trace: dict[str, Any]


class AgentRunHistoryRead(BaseModel):
    id: str
    user_id: str
    run_date: date
    planner: str
    status: str
    context_summary: dict[str, Any]
    candidate_todos: list[dict[str, Any]]
    created_todo_ids: list[str]
    skipped_todos: list[dict[str, Any]]
    explanation: str | None
    decision_trace: dict[str, Any]

    model_config = {"from_attributes": True}
