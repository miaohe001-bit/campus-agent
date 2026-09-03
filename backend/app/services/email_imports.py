import email
import hashlib
import imaplib
import re
from ftfy import fix_text
from datetime import datetime, timezone
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.enums import ApplicationStage, RecruitmentEventType
from app.db.models import Application, Campaign, RecruitmentEvent
from app.schemas.email_imports import EmailImportCreate, EmailImportRead, QQEmailSyncRead
from app.schemas.events import RecruitmentEventCreate
from app.services.events import create_event
from app.services.email_classifier import classify_recruitment_emails
from app.services.email_credentials import (
    decrypt_email_credential,
    get_email_credential,
    mark_email_credential_synced,
)


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
            "\u8fdb\u5165\u9762\u8bd5",
            "\u53c2\u52a0\u9762\u8bd5",
            "\u4e00\u9762",
            "\u4e8c\u9762",
            "\u4e09\u9762",
            "interview invitation",
            "interview scheduled",
        ),
    ),
    (
        RecruitmentEventType.assessment_completed,
        ("\u6d4b\u8bc4\u5b8c\u6210", "assessment completed"),
    ),
    (
        RecruitmentEventType.assessment_received,
        (
            "\u6d4b\u8bc4\u901a\u77e5",
            "\u6d4b\u9a8c\u901a\u77e5",
            "\u6d4b\u8bc4\u9080\u8bf7",
            "\u5728\u7ebf\u6d4b\u8bc4\u9080\u8bf7",
            "\u53c2\u4e0e\u6821\u56ed\u62db\u8058\u5728\u7ebf\u6d4b\u8bc4",
            "assessment invitation",
        ),
    ),
    (
        RecruitmentEventType.written_test_scheduled,
        (
            "\u7b14\u8bd5\u901a\u77e5",
            "\u7b14\u8bd5\u5b89\u6392",
            "\u5728\u7ebf\u7b14\u8bd5",
            "written test",
            "online test",
            "coding test",
        ),
    ),
    (
        RecruitmentEventType.deadline_updated,
        ("\u622a\u6b62\u65f6\u95f4", "\u622a\u6b62\u65e5\u671f", "application deadline", "deadline"),
    ),
    (
        RecruitmentEventType.application_submitted,
        (
            "\u6295\u9012\u6210\u529f",
            "\u7533\u8bf7\u6210\u529f",
            "\u7b80\u5386\u5df2\u6536\u5230",
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
    parsed_override: dict | None = None,
) -> EmailImportRead:
    parsed = parsed_override or parse_recruitment_email(payload)
    event_type = parsed.get("event_type")
    if event_type is None:
        return EmailImportRead(
            imported=False,
            reason=parsed.get("skip_reason") or "email does not look like a supported recruitment event",
            parsed=parsed,
        )

    idempotency_key = _idempotency_key(user_id, payload)
    existing = db.scalar(select(RecruitmentEvent).where(RecruitmentEvent.idempotency_key == idempotency_key))
    application_id, campaign_id = _resolve_related_records(db, user_id=user_id, payload=payload)
    application_id = _ensure_email_application(
        db,
        user_id=user_id,
        application_id=application_id,
        campaign_id=campaign_id,
        event_type=event_type,
        company_name=parsed.get("company_name"),
        position_name=parsed.get("position_name"),
    )
    if existing is not None:
        needs_correction = existing.event_type != event_type
        needs_link_replay = existing.application_id is None and application_id is not None
        needs_position_relink = False
        parsed_position = parsed.get("position_name")
        if existing.application_id and parsed_position:
            linked_application = db.get(Application, existing.application_id)
            needs_position_relink = bool(linked_application and linked_application.position_name != parsed_position.strip())
        if not needs_correction and not needs_link_replay and not needs_position_relink:
            return EmailImportRead(
                imported=False,
                reason="email already imported",
                event=None,
                parsed=parsed,
            )
        correction_kind = "correction" if needs_correction else "position" if needs_position_relink else "linked"
        idempotency_key = f"{idempotency_key}:{correction_kind}:{event_type.value}"
        corrected = db.scalar(select(RecruitmentEvent).where(RecruitmentEvent.idempotency_key == idempotency_key))
        if corrected is not None:
            return EmailImportRead(imported=False, reason="email correction already applied", parsed=parsed)

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
    credential = get_email_credential(db, user_id=user_id)
    if credential is None:
        return QQEmailSyncRead(
            ok=False,
            scanned_count=0,
            imported_count=0,
            skipped_count=0,
            reason="QQ email is not configured for this user",
        )

    try:
        email_address, authorization_code = decrypt_email_credential(credential)
    except RuntimeError as error:
        return QQEmailSyncRead(
            ok=False,
            scanned_count=0,
            imported_count=0,
            skipped_count=0,
            reason=str(error),
        )

    imports: list[EmailImportRead] = []
    payloads: list[EmailImportCreate] = []
    with imaplib.IMAP4_SSL(settings.qq_imap_host, settings.qq_imap_port) as client:
        client.login(email_address, authorization_code)
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
            payloads.append(_email_payload_from_raw(raw_message))

    ai_decisions, ai_error = classify_recruitment_emails(payloads)
    for index, payload in enumerate(payloads):
        decision = ai_decisions.get(index)
        if decision and decision.get("confidence") == "high" and decision.get("is_recruitment") and decision.get("event_type"):
            parsed = {
                "event_type": RecruitmentEventType(decision["event_type"]),
                "confidence": "ai_high",
                "company_name": decision.get("company_name"),
                "position_name": decision.get("position_name"),
                "scheduled_at": decision.get("scheduled_at"),
                "deadline_at": decision.get("deadline_at"),
                "evidence": decision.get("evidence"),
                "normalized_subject": _repair_mojibake(payload.subject),
            }
            imports.append(import_mock_email(db, user_id=user_id, payload=payload, parsed_override=parsed))
        elif decision and decision.get("confidence") in {"low", "medium"} and decision.get("is_recruitment"):
            imports.append(EmailImportRead(imported=False, reason="recruitment email needs confirmation", parsed=decision))
        else:
            imports.append(import_mock_email(db, user_id=user_id, payload=payload))

    result = QQEmailSyncRead(
        ok=ai_error is None,
        scanned_count=len(imports),
        imported_count=sum(1 for item in imports if item.imported),
        skipped_count=sum(1 for item in imports if not item.imported),
        reason=f"AI email parser unavailable: {ai_error}" if ai_error else None,
        imports=imports,
    )
    mark_email_credential_synced(db, credential, datetime.now(timezone.utc))
    return result


def parse_recruitment_email(payload: EmailImportCreate) -> dict:
    subject = _repair_mojibake(payload.subject or "")
    body = _repair_mojibake(payload.body or "")
    from_address = _repair_mojibake(payload.from_address or "")
    text = f"{subject}\n{body}\n{from_address}".lower()
    has_negative_hint = _has_negative_hint(text)
    has_hint = _has_recruitment_hint(text)
    subject_event_type = _detect_event_type(subject.lower())
    event_type = subject_event_type or (_detect_event_type(text) if has_hint and not has_negative_hint else None)
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
        if _repair_mojibake(item.company_name).lower() in text and _repair_mojibake(item.position_name).lower() in text
    ]
    if len(exact_matches) == 1:
        item = exact_matches[0]
        return item.id, item.campaign_id

    company_matches = [item for item in applications if _repair_mojibake(item.company_name).lower() in text]
    if len(company_matches) == 1:
        item = company_matches[0]
        return item.id, item.campaign_id

    position_matches = [item for item in applications if _repair_mojibake(item.position_name).lower() in text]
    if len(position_matches) == 1:
        item = position_matches[0]
        return item.id, item.campaign_id

    campaigns = db.scalars(select(Campaign).order_by(Campaign.created_at.desc()).limit(50)).all()
    for item in campaigns:
        if _repair_mojibake(item.company_name).lower() in text or _repair_mojibake(item.name).lower() in text:
            return None, item.id

    if len(applications) == 1:
        return applications[0].id, applications[0].campaign_id
    return None, None


def _ensure_email_application(
    db: Session,
    *,
    user_id: str,
    application_id: str | None,
    campaign_id: str | None,
    event_type: RecruitmentEventType,
    company_name: str | None = None,
    position_name: str | None = None,
) -> str | None:
    if application_id is not None:
        return application_id
    if event_type not in {
        RecruitmentEventType.application_submitted,
        RecruitmentEventType.assessment_received,
        RecruitmentEventType.assessment_completed,
        RecruitmentEventType.written_test_scheduled,
        RecruitmentEventType.interview_scheduled,
        RecruitmentEventType.offer_received,
        RecruitmentEventType.rejected,
        RecruitmentEventType.interview_rescheduled,
        RecruitmentEventType.interview_canceled,
    }:
        return None
    if company_name:
        company_applications = db.scalars(
            select(Application)
            .where(Application.user_id == user_id)
            .where(Application.company_name == company_name.strip())
            .where(Application.deleted_at.is_(None))
            .order_by(Application.last_changed_at.desc())
        ).all()
        if position_name:
            exact = next((item for item in company_applications if item.position_name == position_name.strip()), None)
            if exact is not None:
                return exact.id
        elif len(company_applications) == 1:
            return company_applications[0].id
    if campaign_id is not None:
        existing = db.scalar(
            select(Application)
            .where(Application.user_id == user_id)
            .where(Application.campaign_id == campaign_id)
            .where(Application.deleted_at.is_(None))
            .order_by(Application.last_changed_at.desc())
        )
        if existing is not None:
            return existing.id
    campaign = db.get(Campaign, campaign_id) if campaign_id else None
    resolved_company = company_name.strip() if company_name else (_repair_mojibake(campaign.company_name) if campaign else None)
    if not resolved_company:
        return None
    application = Application(
        user_id=user_id,
        campaign_id=campaign_id,
        company_name=resolved_company,
        position_name=position_name.strip() if position_name else "岗位待确认",
        stage=ApplicationStage.submitted,
        source="email",
    )
    db.add(application)
    db.flush()
    return application.id


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
    current = fix_text(value)
    for _ in range(3):
        if not any(marker in current for marker in ("Ã", "Â", "å", "æ", "ç", "è", "é", "ð")):
            break
        try:
            repaired = current.encode("latin1").decode("utf-8")
        except UnicodeError:
            break
        if not _looks_more_readable(repaired, current):
            break
        current = repaired
    return current


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
