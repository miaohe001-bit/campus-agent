import json
import logging
from typing import Any

from openai import OpenAI, OpenAIError
from ftfy import fix_text

from app.core.config import settings
from app.schemas.email_imports import EmailImportCreate

logger = logging.getLogger(__name__)


ALLOWED_EVENTS = {
    "application_submitted", "assessment_received", "assessment_completed",
    "written_test_scheduled", "interview_scheduled", "interview_rescheduled",
    "interview_canceled", "offer_received", "rejected", "deadline_updated",
}


def classify_recruitment_emails(payloads: list[EmailImportCreate]) -> tuple[dict[int, dict[str, Any]], str | None]:
    """Classify one IMAP window in a single structured LLM call.

    The returned decisions are advisory. Business services still validate event types,
    confidence, relationships and idempotency before writing anything.
    """
    if not payloads or not settings.openai_api_key:
        return {}, "OPENAI_API_KEY is not configured" if payloads else None
    client_args: dict[str, Any] = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        client_args["base_url"] = settings.openai_base_url
    client = OpenAI(**client_args)
    emails = [{
        "index": index,
        "from": fix_text(item.from_address or ""),
        "subject": fix_text(item.subject),
        "body": _compact_body(fix_text(item.body)),
        "received_at": item.received_at.isoformat() if item.received_at else None,
    } for index, item in enumerate(payloads)]
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {"role": "system", "content": (
                    "你是校园招聘邮件解析器。只依据邮件原文判断，不补充不存在的信息。"
                    "区分投递成功、测评、笔试、面试、Offer 和明确淘汰/流程结束。"
                    "正文中的免责声明、系统说明或‘未通过验证’不得判为淘汰。"
                    "广告、验证码、会员和普通工作邮件不是招聘进展。返回 JSON，禁止解释性文本。"
                )},
                {"role": "user", "content": json.dumps({
                    "emails": emails,
                    "output_schema": {"results": [{
                        "index": "integer",
                        "is_recruitment": "boolean",
                        "event_type": "application_submitted | assessment_received | assessment_completed | written_test_scheduled | interview_scheduled | interview_rescheduled | interview_canceled | offer_received | rejected | deadline_updated | null",
                        "company_name": "string or null",
                        "position_name": "string or null",
                        "scheduled_at": "ISO datetime or null",
                        "deadline_at": "ISO datetime or null",
                        "confidence": "high | medium | low",
                        "evidence": "邮件中的简短依据",
                    }]}
                }, ensure_ascii=False)},
            ],
        )
        raw = _loads_json_object(response.choices[0].message.content or "")
    except (OpenAIError, json.JSONDecodeError, TypeError, AttributeError) as error:
        logger.warning("Email AI classification failed: %s: %s", type(error).__name__, str(error)[:500])
        return {}, f"{type(error).__name__}: {str(error)[:300]}"
    decisions: dict[int, dict[str, Any]] = {}
    for item in raw.get("results", []):
        if not isinstance(item, dict) or not isinstance(item.get("index"), int):
            continue
        event_type = item.get("event_type")
        if event_type is not None and event_type not in ALLOWED_EVENTS:
            continue
        for field in ("company_name", "position_name", "evidence"):
            if isinstance(item.get(field), str):
                item[field] = fix_text(item[field]).strip()
        decisions[item["index"]] = item
    return decisions, None


def _compact_body(value: str) -> str:
    text = " ".join(value.split())
    if len(text) <= 2200:
        return text
    # Recruitment facts are normally concentrated near the beginning, while
    # deadlines, disclaimers and contact details often appear near the end.
    return f"{text[:1600]}\n…\n{text[-600:]}"


def _loads_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if not text:
        raise json.JSONDecodeError("empty model response", content, 0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise
        return json.loads(text[start:end + 1])
