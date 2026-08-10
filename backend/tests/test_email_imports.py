from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.enums import RecruitmentEventType
from app.main import create_app
from app.schemas.email_imports import EmailImportCreate
from app.services.email_imports import parse_recruitment_email


def test_parse_interview_invitation() -> None:
    parsed = parse_recruitment_email(
        EmailImportCreate(
            provider="mock",
            subject="字节跳动面试邀请",
            body="你的面试安排在 2026-08-06 10:00，请准时参加。",
        )
    )

    assert parsed["event_type"] == RecruitmentEventType.interview_scheduled
    assert parsed["scheduled_at"] == "2026-08-06T10:00:00"


def test_skip_marketing_email_with_offer_word() -> None:
    parsed = parse_recruitment_email(
        EmailImportCreate(
            provider="mock",
            subject="New Courses and Workshops",
            body="Special offer for members. VIP course discount available today.",
        )
    )

    assert parsed["event_type"] is None
    assert parsed["has_negative_hint"] is True


def test_parse_application_submitted() -> None:
    parsed = parse_recruitment_email(
        EmailImportCreate(
            provider="mock",
            subject="【搜狐畅游】校园招聘简历投递成功",
            body="我们已收到你的申请，请等待后续通知。",
        )
    )

    assert parsed["event_type"] == RecruitmentEventType.application_submitted


def test_parse_chinese_interview_datetime() -> None:
    parsed = parse_recruitment_email(
        EmailImportCreate(
            provider="mock",
            subject="腾讯产品经理面试通知",
            body="面试安排：8月16日下午 2:30，请提前进入会议。",
            received_at=datetime(2026, 8, 10, 9, 0),
        )
    )

    assert parsed["scheduled_at"] == "2026-08-16T14:30:00"


def test_email_matches_exact_position_and_updates_same_schedule() -> None:
    client = TestClient(create_app())
    user_id = f"test-email-flow-{uuid4()}"
    campaign = client.post(
        "/campaigns",
        json={"company_name": "腾讯", "name": "腾讯 2027 校园招聘", "status": "open"},
    ).json()["data"]
    product = client.post(
        f"/applications?user_id={user_id}",
        json={"campaign_id": campaign["id"], "company_name": "腾讯", "position_name": "产品经理"},
    ).json()["data"]
    client.post(
        f"/applications?user_id={user_id}",
        json={"campaign_id": campaign["id"], "company_name": "腾讯", "position_name": "产品运营"},
    )

    first = client.post(
        f"/email-imports/mock?user_id={user_id}",
        json={
            "provider": "mock",
            "message_id": f"invite-{uuid4()}",
            "subject": "腾讯产品经理面试通知",
            "body": "面试安排在 2026-08-16 14:30，请准时参加。",
        },
    ).json()["data"]
    rescheduled = client.post(
        f"/email-imports/mock?user_id={user_id}",
        json={
            "provider": "mock",
            "message_id": f"reschedule-{uuid4()}",
            "subject": "腾讯产品经理面试改期",
            "body": "重新安排面试时间为 2026-08-17 10:00。",
        },
    ).json()["data"]

    assert first["event"]["application_id"] == product["id"]
    assert rescheduled["event"]["application_id"] == product["id"]
    schedules = client.get(f"/schedules?user_id={user_id}").json()["data"]["items"]
    interviews = [item for item in schedules if item["schedule_type"] == "interview"]
    assert len(interviews) == 1
    assert interviews[0]["starts_at"].startswith("2026-08-17T10:00:00")
    assert interviews[0]["reminder_minutes"] == [1440, 120]
    assert len(interviews[0]["change_log"]) == 2


def test_duplicate_email_does_not_duplicate_event_or_schedule() -> None:
    client = TestClient(create_app())
    user_id = f"test-email-dedupe-{uuid4()}"
    application = client.post(
        f"/applications?user_id={user_id}",
        json={"company_name": "字节跳动", "position_name": "产品经理"},
    ).json()["data"]
    payload = {
        "provider": "mock",
        "message_id": f"same-message-{uuid4()}",
        "subject": "字节跳动产品经理笔试通知",
        "body": "在线笔试安排在 2026-08-18 19:00。",
        "application_id": application["id"],
    }

    first = client.post(f"/email-imports/mock?user_id={user_id}", json=payload).json()["data"]
    second = client.post(f"/email-imports/mock?user_id={user_id}", json=payload).json()["data"]

    assert first["imported"] is True
    assert second["imported"] is False
    schedules = client.get(f"/schedules?user_id={user_id}").json()["data"]["items"]
    assert len([item for item in schedules if item["schedule_type"] == "written_test"]) == 1
