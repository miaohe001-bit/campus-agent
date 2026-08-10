import json

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.agent import PlannerContext, PlannerTodoCandidate, RecruitmentArticleDecision


class LLMPlanner:
    name = "openai_compatible"

    def classify_recruitment_article(self, article: dict) -> tuple[RecruitmentArticleDecision, dict]:
        if not settings.openai_api_key:
            return RecruitmentArticleDecision(reason="OPENAI_API_KEY is not configured"), {
                "planner": "fallback_without_openai_api_key",
                "reason": "OPENAI_API_KEY is not configured",
            }

        client_kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        client = OpenAI(**client_kwargs)

        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You classify official WeChat articles for a campus recruitment assistant. "
                            "Return JSON only. Mark true only when the article is likely an official company "
                            "campus recruitment, school recruitment, internship recruitment, or application "
                            "opening/deadline article. Be conservative with third-party summaries, referral-code "
                            "posts, generic job-hunting notes, and influencer collections."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "article": article,
                                "output_schema": {
                                    "is_official_recruitment": "boolean",
                                    "confidence": "low | medium | high",
                                    "company_name": "string or null",
                                    "graduation_year": "string or null",
                                    "campaign_name": "string or null",
                                    "position_categories": "array of strings or null",
                                    "cities": "array of strings or null",
                                    "deadline_at": "ISO datetime string or yyyy-MM-dd string or null",
                                    "published_at": "yyyy-MM-dd string or null",
                                    "application_url": "string or null",
                                    "reason": "string or null",
                                },
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
            )
            content = response.choices[0].message.content or "{}"
            raw = _loads_json_object(content)
            return RecruitmentArticleDecision.model_validate(raw), {
                "planner": self.name,
                "base_url": settings.openai_base_url or "https://api.openai.com/v1",
                "model": settings.openai_model,
            }
        except (OpenAIError, json.JSONDecodeError, ValidationError) as error:
            return RecruitmentArticleDecision(reason=str(error)[:500]), {
                "planner": "fallback_after_llm_error",
                "base_url": settings.openai_base_url or "https://api.openai.com/v1",
                "model": settings.openai_model,
                "error_type": type(error).__name__,
                "reason": str(error)[:500],
            }

    def plan_today(self, context: PlannerContext) -> tuple[list[PlannerTodoCandidate], dict]:
        if not settings.openai_api_key:
            return _fallback_plan(context), {
                "planner": "fallback_without_openai_api_key",
                "reason": "OPENAI_API_KEY is not configured",
            }

        client_kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        client = OpenAI(**client_kwargs)

        try:
            response = client.chat.completions.create(
                model=settings.openai_model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the MVP planner for a campus recruitment assistant. "
                            "Return JSON only. Create at most 3 practical todos for today. "
                            "All todo titles and business reasons must be written in Simplified Chinese. "
                            "The total estimated minutes must not exceed context.available_minutes. "
                            "Do not invent new product features. Prefer urgent schedules, active applications, "
                            "and relevant open campaigns. Each todo must be concise."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "context": context.model_dump(mode="json"),
                                "output_schema": {
                                    "todos": [
                                        {
                                            "title": "string",
                                            "estimated_minutes": "integer or null",
                                            "business_reason": "string or null",
                                            "application_id": "string or null",
                                            "campaign_id": "string or null",
                                        }
                                    ]
                                },
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
            )
            content = response.choices[0].message.content or "{}"
            raw = _loads_json_object(content)
        except (OpenAIError, json.JSONDecodeError) as error:
            return _fallback_plan(context), {
                "planner": "fallback_after_llm_error",
                "base_url": settings.openai_base_url or "https://api.openai.com/v1",
                "model": settings.openai_model,
                "error_type": type(error).__name__,
                "reason": str(error)[:500],
            }
        todos = _parse_candidates(raw.get("todos", []))
        return todos[:3], {
            "planner": self.name,
            "base_url": settings.openai_base_url or "https://api.openai.com/v1",
            "model": settings.openai_model,
            "raw_todo_count": len(raw.get("todos", [])),
        }


def _parse_candidates(items: list[dict]) -> list[PlannerTodoCandidate]:
    candidates: list[PlannerTodoCandidate] = []
    for item in items:
        try:
            candidates.append(PlannerTodoCandidate.model_validate(item))
        except ValidationError:
            continue
    return candidates


def _loads_json_object(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(content[start : end + 1])


def _fallback_plan(context: PlannerContext) -> list[PlannerTodoCandidate]:
    candidates: list[PlannerTodoCandidate] = []

    for schedule in context.schedules[:2]:
        candidates.append(
            PlannerTodoCandidate(
                title=f"确认日程：{schedule['title']}",
                estimated_minutes=15,
                business_reason="近期有待进行的招聘日程，需要先确认时间和准备事项。",
                application_id=schedule.get("application_id"),
                campaign_id=schedule.get("campaign_id"),
            )
        )

    for application in context.applications:
        if application.get("stage") != "failed":
            candidates.append(
                PlannerTodoCandidate(
                    title=f"跟进 {application['company_name']} {application['position_name']} 进度",
                    estimated_minutes=20,
                    business_reason="存在进行中的投递记录，今天适合检查状态并补充下一步。",
                    application_id=application.get("id"),
                    campaign_id=application.get("campaign_id"),
                )
            )
            break

    if not candidates and context.campaigns:
        campaign = context.campaigns[0]
        candidates.append(
            PlannerTodoCandidate(
                title=f"查看 {campaign['company_name']} 的招聘机会",
                estimated_minutes=20,
                business_reason="当前有开放招聘项目，可先判断是否匹配目标。",
                campaign_id=campaign.get("id"),
            )
        )

    if not candidates:
        candidates.append(
            PlannerTodoCandidate(
                title="补充秋招目标和已有投递记录",
                estimated_minutes=15,
                business_reason="当前信息不足，先补齐目标和投递记录，后续计划会更准确。",
            )
        )

    return candidates[:3]
