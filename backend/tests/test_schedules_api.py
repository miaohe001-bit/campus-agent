from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def test_schedule_reminders_have_defaults_and_can_be_disabled() -> None:
    client = TestClient(create_app())
    user_id = f"test-schedule-reminders-{uuid4()}"
    created = client.post(
        f"/schedules?user_id={user_id}",
        json={
            "title": "产品经理一面",
            "schedule_type": "interview",
            "starts_at": "2026-08-20T10:00:00",
            "source": "manual",
        },
    ).json()["data"]

    assert created["reminder_minutes"] == [1440, 120]

    updated = client.patch(
        f"/schedules/{created['id']}?user_id={user_id}",
        json={"reminder_minutes": []},
    ).json()["data"]

    assert updated["reminder_minutes"] == []
    assert updated["change_log"][-1]["changes"]["reminder_minutes"] == []
