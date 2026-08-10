import email
import hashlib
import imaplib
import re
from datetime import datetime
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.enums import RecruitmentEventType
from app.db.models import Application, Campaign, RecruitmentEvent
from app.schemas.email_imports import EmailImportCreate, EmailImportRead, QQEmailSyncRead
from app.schemas.events import RecruitmentEventCreate
from app.services.events import create_event


RECRUITMENT_HINTS = (
    "\u62db\u8058",
    "\u6821\u62db",
    "\u6821\u56ed\u62db\u8058",
    "\u5185\u63a8",
    "\u7b80\u5386",
    "\u6295\u9012",
    "\u7533\u8bf7",
    "\u5019\u9009\u4eba",
    "\u9762\u8bd5",
    "\u7b14\u8bd5",
    "\u6d4b\u8bc4",
    "\u5f55\u7528",
    "recruit",
    "career",
    "campus",
    "job",
    "candidate",
    "application",
    "interview",
    "assessment",
    "hire",
    "talent",
)

RECRUITMENT_SENDER_HINTS = (
    "hire",
    "career",
    "recruit",
    "talent",
    "job",
    "campus",
    "noreply-hire",
    "mokahr",
    "nowcoder",
    "liepin",
    "zhaopin",
    "51job",
    "lagou",
    "moka",
    "beisen",
    "bytedance",
    "tencent",
    "baidu",
    "alibaba",
    "meituan",
    "jd",
    "pdd",
    "shopee",
)

NEGATIVE_HINTS = (
    "\u4f1a\u5458",
    "\u4f1a\u5458\u5f00\u901a",
    "\u817e\u8baf\u89c6\u9891",
    "vip",
    "\u4f01\u4e1a\u90ae",
    "\u597d\u53cb\u751f\u65e5",
    "\u9000\u4fe1",
    "\u9a8c\u8bc1\u7801",
    "\u91cd\u7f6e\u5bc6\u7801",
    "\u4fe1\u7528\u5361",
    "\u4e13\u5c5e\u5361",
    "\u8865\u8d34",
    "\u5e7f\u544a",
    "(ad)",
    "\u7ffb\u8bd1\u5b98",
    "\u4fbf\u6377\u626b\u63cf",
    "newsletter",
    "workshop",
    "course",
)

EVENT_KEYWORDS: list[tuple[RecruitmentEventType, tuple[str, ...]]] = [
    (
        RecruitmentEventType.rejected,
        (
            "\u672a\u901a\u8fc7",
            "\u4e0d\u901a\u8fc7",
            "\u9057\u61be",
            "\u5f88\u9057\u61be",
            "\u6682\u4e0d\u5339\u914d",
            "reject",
            "rejected",
            "not selected",
            "unfortunately",
        ),
    ),
    (
        RecruitmentEventType.offer_received,
        (
            "\u5f55\u7528\u901a\u77e5",
            "\u5f55\u7528\u610f\u5411",
            "\u53d1\u653e\u610f\u5411",
            "\u6b22\u8fce\u52a0\u5165",
            "\u5f55\u53d6\u901a\u77e5",
            "offer letter",
            "employment offer",
            "job offer",
        ),
    ),
    (
        RecruitmentEventType.interview_rescheduled,
        (
            "\u9762\u8bd5\u6539\u671f",
            "\u9762\u8bd5\u65f6\u95f4\u53d8\u66f4",
            "\u91cd\u65b0\u5b89\u6392\u9762\u8bd5",
            "reschedule",
            "rescheduled",
        ),
    ),
    (
        RecruitmentEventType.interview_canceled,
        (
            "\u9762\u8bd5\u53d6\u6d88",
            "\u53d6\u6d88\u9762\u8bd5",
            "interview canceled",
            "cancelled interview",
        ),
    ),
    (
        RecruitmentEventType.interview_scheduled,
        (
            "\u9762\u8bd5\u9080\u8bf7",
            "\u9762\u8bd5\u901a\u77e5",
            "\u9762\u8bd5\u5b89\u6392",
            "\u4e00\u9762",
            "\u4e8c\u9762",
            "\u4e09\u9762",
            "interview invitation",
            "interview scheduled",
        ),
    ),
    (
        RecruitmentEventType.written_test_scheduled,
        (
            "\u7b14\u8bd5\u901a\u77e5",
            "\u7b14\u8bd5\u5b89\u6392",
            "\u5728\u7ebf\u6d4b\u8bc4",
            "\u5728\u7ebf\u7b14\u8bd5",
            "written test",
            "online test",
            "coding test",
        ),
    ),
    (
        RecruitmentEventType.assessment_completed,
        ("\u6d4b\u8bc4\u5b8c\u6210", "assessment completed"),
    ),
    (
        RecruitmentEventType.assessment_received,
        ("\u6d4b\u8bc4\u901a\u77e5", "\u6d4b\u9a8c\u901a\u77e5", "assessment invitation"),
    ),
    (
        RecruitmentEventType.deadline_updated,
        ("\u622a\u6b62\u65f6\u95f4", "\u622a\u6b62\u65e5\u671f", "application deadline", "deadline"),
    ),
    (
        RecruitmentEventType.application_submitted,
        (
            "\u6295\u9012\u6210\u529f",
            "\u5df2\u6536\u5230\u4f60\u7684\u7533\u8bf7",
            "\u7b80\u5386\u6295\u9012",
            "application received",
            "application submitted",
        ),
    ),
]

DATETIME_PATTERNS = (
    re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?"),
    re.compile(r"\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}"),
    re.compile(r"\d{4}年\d{1,2}月\d{1,2}日\s*(?:上午|下午)?\s*\d{1,2}[：:]\d{2}"),
    re.compile(r"\d{1,2}月\d{1,2}日\s*(?:上午|下午)?\s*\d{1,2}[：:]\d{2}"),
)


def import_mock_email(
    db: Session,
    *,
    user_id: str,
    payload: EmailImportCreate,
) -> EmailImportRead:
    parsed = parse_recruitment_email(payload)
    event_type = parsed.get("event_type")
    if event_type is None:
        return EmailImportRead(
            imported=False,
            reason=parsed.get("skip_reason") or "email does not look like a supported recruitment event",
            parsed=parsed,
        )

    idempotency_key = _idempotency_key(user_id, payload)
    existing = db.scalar(select(RecruitmentEvent).where(RecruitmentEvent.idempotency_key == idempotency_key))
    if existing is not None:
        return EmailImportRead(
            imported=False,
            reason="email already imported",
            event=None,
            parsed=parsed,
        )
    application_id, campaign_id = _resolve_related_records(db, user_id=user_id, payload=payload)

    event_payload = {
        "title": _event_title(payload, event_type),
        "email": {
            "provider": payload.provider,
            "message_id": payload.message_id,
            "from_address": payload.from_address,
            "subject": payload.subject,
        },
        "parser": parsed,
    }
    parsed_time = parsed.get("scheduled_at") or parsed.get("deadline_at")
    if parsed_time:
        if event_type in {
            RecruitmentEventType.interview_scheduled,
            RecruitmentEventType.interview_rescheduled,
            RecruitmentEventType.written_test_scheduled,
        }:
            event_payload["scheduled_at"] = parsed_time
        else:
            event_payload["deadline_at"] = parsed_time

    event = create_event(
        db,
        user_id=user_id,
        payload=RecruitmentEventCreate(
            application_id=application_id,
            campaign_id=campaign_id,
            event_type=event_type,
            occurred_at=payload.received_at,
            source=f"email:{payload.provider}",
            payload=event_payload,
            idempotency_key=idempotency_key,
        ),
    )
    return EmailImportRead(imported=True, event=event, parsed=parsed)


def sync_qq_email(db: Session, *, user_id: str) -> QQEmailSyncRead:
    if not settings.qq_email_address or not settings.qq_email_authorization_code:
        return QQEmailSyncRead(
            ok=False,
            scanned_count=0,
            imported_count=0,
            skipped_count=0,
            reason="QQ email address or authorization code is not configured",
        )

    imports: list[EmailImportRead] = []
    with imaplib.IMAP4_SSL(settings.qq_imap_host, settings.qq_imap_port) as client:
        client.login(settings.qq_email_address, settings.qq_email_authorization_code)
        client.select(settings.qq_imap_mailbox, readonly=True)
        status, data = client.search(None, "ALL")
        if status != "OK" or not data or not data[0]:
            return QQEmailSyncRead(ok=True, scanned_count=0, imported_count=0, skipped_count=0, imports=[])

        message_numbers = data[0].split()[-settings.qq_imap_fetch_limit :]
        for message_number in message_numbers:
            status, fetched = client.fetch(message_number, "(RFC822)")
            if status != "OK" or not fetched:
                continue
            raw_message = _first_raw_message(fetched)
            if raw_message is None:
                continue
            payload = _email_payload_from_raw(raw_message)
            imports.append(import_mock_email(db, user_id=user_id, payload=payload))

    return QQEmailSyncRead(
        ok=True,
        scanned_count=len(imports),
        imported_count=sum(1 for item in imports if item.imported),
        skipped_count=sum(1 for item in imports if not item.imported),
        imports=imports,
    )


def parse_recruitment_email(payload: EmailImportCreate) -> dict:
    subject = _repair_mojibake(payload.subject or "")
    body = _repair_mojibake(payload.body or "")
    from_address = _repair_mojibake(payload.from_address or "")
    text = f"{subject}\n{body}\n{from_address}".lower()
    has_negative_hint = _has_negative_hint(text)
    has_hint = _has_recruitment_hint(text)
    event_type = _detect_event_type(text) if has_hint and not has_negative_hint else None
    parsed: dict = {
        "event_type": event_type,
        "confidence": "rule_based" if event_type else "none",
        "has_recruitment_hint": has_hint,
        "has_negative_hint": has_negative_hint,
        "normalized_subject": subject,
    }
    if has_negative_hint:
        parsed["skip_reason"] = "looks like non-recruitment system or marketing email"
    elif not has_hint:
        parsed["skip_reason"] = "missing recruitment hint"
    parsed_time = _extract_datetime(text, reference=payload.received_at)
    if parsed_time and event_type in {
        RecruitmentEventType.interview_scheduled,
        RecruitmentEventType.interview_rescheduled,
        RecruitmentEventType.written_test_scheduled,
    }:
        parsed["scheduled_at"] = parsed_time
    elif parsed_time and event_type is not None:
        parsed["deadline_at"] = parsed_time
    return parsed


def _has_recruitment_hint(text: str) -> bool:
    return any(hint in text for hint in RECRUITMENT_HINTS + RECRUITMENT_SENDER_HINTS)


def _has_negative_hint(text: str) -> bool:
    return any(hint in text for hint in NEGATIVE_HINTS)


def _detect_event_type(text: str) -> RecruitmentEventType | None:
    for event_type, keywords in EVENT_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return event_type
    return None


def _extract_datetime(text: str, *, reference: datetime | None = None) -> str | None:
    for pattern in DATETIME_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        matched = match.group(0)
        if "月" in matched:
            return _parse_chinese_datetime(matched, reference=reference)
        raw = matched.replace("/", "-").replace(" ", "T")
        try:
            return datetime.fromisoformat(raw).isoformat()
        except ValueError:
            return raw
    return None


def _parse_chinese_datetime(value: str, *, reference: datetime | None) -> str | None:
    match = re.search(
        r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日\s*(上午|下午)?\s*(\d{1,2})[：:](\d{2})",
        value,
    )
    if match is None:
        return None
    year = int(match.group(1) or (reference or datetime.now()).year)
    hour = int(match.group(5))
    if match.group(4) == "下午" and hour < 12:
        hour += 12
    if match.group(4) == "上午" and hour == 12:
        hour = 0
    try:
        return datetime(
            year,
            int(match.group(2)),
            int(match.group(3)),
            hour,
            int(match.group(6)),
        ).isoformat()
    except ValueError:
        return None


def _event_title(payload: EmailImportCreate, event_type: RecruitmentEventType) -> str:
    if event_type in {
        RecruitmentEventType.interview_scheduled,
        RecruitmentEventType.interview_rescheduled,
        RecruitmentEventType.written_test_scheduled,
    }:
        return _repair_mojibake(payload.subject)
    return event_type.value


def _resolve_related_records(
    db: Session,
    *,
    user_id: str,
    payload: EmailImportCreate,
) -> tuple[str | None, str | None]:
    if payload.application_id or payload.campaign_id:
        return payload.application_id, payload.campaign_id

    text = _repair_mojibake(f"{payload.subject}\n{payload.body}\n{payload.from_address or ''}").lower()
    applications = db.scalars(
        select(Application)
        .where(Application.user_id == user_id)
        .where(Application.deleted_at.is_(None))
        .order_by(Application.last_changed_at.desc())
        .limit(50)
    ).all()
    exact_matches = [
        item
        for item in applications
        if item.company_name.lower() in text and item.position_name.lower() in text
    ]
    if len(exact_matches) == 1:
        item = exact_matches[0]
        return item.id, item.campaign_id

    company_matches = [item for item in applications if item.company_name.lower() in text]
    if len(company_matches) == 1:
        item = company_matches[0]
        return item.id, item.campaign_id

    position_matches = [item for item in applications if item.position_name.lower() in text]
    if len(position_matches) == 1:
        item = position_matches[0]
        return item.id, item.campaign_id

    campaigns = db.scalars(select(Campaign).order_by(Campaign.created_at.desc()).limit(50)).all()
    for item in campaigns:
        if item.company_name.lower() in text or item.name.lower() in text:
            return None, item.id

    if len(applications) == 1:
        return applications[0].id, applications[0].campaign_id
    return None, None


def _idempotency_key(user_id: str, payload: EmailImportCreate) -> str:
    if payload.message_id:
        return f"email:{payload.provider}:{user_id}:{payload.message_id}"
    digest = hashlib.sha256(
        f"{user_id}|{payload.provider}|{payload.from_address}|{payload.subject}|{payload.body}".encode("utf-8")
    ).hexdigest()
    return f"email:{payload.provider}:{digest}"


def _first_raw_message(fetched: list | tuple) -> bytes | None:
    for item in fetched:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            return item[1]
    return None


def _email_payload_from_raw(raw_message: bytes) -> EmailImportCreate:
    message = email.message_from_bytes(raw_message)
    return EmailImportCreate(
        provider="qq",
        message_id=_decode_header_value(message.get("Message-ID")) or _fallback_message_id(raw_message),
        from_address=_decode_header_value(message.get("From")),
        subject=_decode_header_value(message.get("Subject")) or "(no subject)",
        body=_extract_body(message),
        received_at=_parse_message_date(message.get("Date")),
    )


def _decode_header_value(value: str | None) -> str | None:
    if value is None:
        return None
    decoded_parts: list[str] = []
    for part, encoding in decode_header(value):
        if isinstance(part, bytes):
            decoded_parts.append(_decode_bytes(part, encoding))
        else:
            decoded_parts.append(part)
    return _repair_mojibake("".join(decoded_parts).strip())


def _decode_bytes(value: bytes, encoding: str | None) -> str:
    encodings = [encoding, "utf-8", "gb18030", "gbk", "big5"]
    for candidate in encodings:
        if not candidate:
            continue
        try:
            return value.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue
    return value.decode("utf-8", errors="replace")


def _extract_body(message: Message) -> str:
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                continue
            if content_type == "text/plain":
                return _decode_message_part(part)
        for part in message.walk():
            if part.get_content_type() == "text/html":
                return _strip_html(_decode_message_part(part))
        return ""
    if message.get_content_type() == "text/html":
        return _strip_html(_decode_message_part(message))
    return _decode_message_part(message)


def _decode_message_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        raw_payload = part.get_payload()
        return _repair_mojibake(raw_payload if isinstance(raw_payload, str) else "")
    charset = part.get_content_charset()
    return _repair_mojibake(_decode_bytes(payload, charset))


def _repair_mojibake(value: str) -> str:
    if not value:
        return value
    if not any(marker in value for marker in ("Ã", "Â", "å", "æ", "ç", "è", "é", "ð")):
        return value
    try:
        repaired = value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value
    return repaired if _looks_more_readable(repaired, value) else value


def _looks_more_readable(candidate: str, original: str) -> bool:
    bad_markers = ("Ã", "Â", "å", "æ", "ç", "è", "é")
    return sum(candidate.count(item) for item in bad_markers) < sum(original.count(item) for item in bad_markers)


def _strip_html(value: str) -> str:
    value = re.sub(r"<(br|p|div|li|tr|h\d)[^>]*>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _parse_message_date(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def _fallback_message_id(raw_message: bytes) -> str:
    return hashlib.sha256(raw_message).hexdigest()
