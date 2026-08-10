from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def test_due_notification_is_idempotent_and_can_be_read() -> None:
    client = TestClient(create_app())
    user_id = f"test-notification-{uuid4()}"
    event_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    schedule = client.post(
        f"/schedules?user_id={user_id}",
        json={
            "title": "产品经理面试",
            "schedule_type": "interview",
            "starts_at": event_at.isoformat(),
            "reminder_minutes": [60],
        },
    ).json()["data"]

    first = client.get(f"/notifications?user_id={user_id}").json()["data"]["items"]
    second = client.get(f"/notifications?user_id={user_id}").json()["data"]["items"]

    assert len(first) == 1
    assert first[0]["schedule_id"] == schedule["id"]
    assert first[0]["id"] == second[0]["id"]

    response = client.patch(
        f"/notifications/{first[0]['id']}/read?user_id={user_id}"
    )
    assert response.status_code == 200
    assert client.get(f"/notifications?user_id={user_id}").json()["data"]["items"] == []


def test_reschedule_replaces_pending_reminder() -> None:
    client = TestClient(create_app())
    user_id = f"test-reminder-{uuid4()}"
    original = datetime.now(timezone.utc) + timedelta(days=2)
    created = client.post(
        f"/schedules?user_id={user_id}",
        json={
            "title": "笔试",
            "schedule_type": "written_test",
            "starts_at": original.isoformat(),
            "reminder_minutes": [1440],
        },
    ).json()["data"]
    changed = original + timedelta(days=1)

    client.patch(
        f"/schedules/{created['id']}?user_id={user_id}",
        json={"starts_at": changed.isoformat()},
    )

    from app.db.models import ReminderNotification
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        reminders = db.query(ReminderNotification).filter_by(schedule_id=created["id"]).all()
        assert len(reminders) == 2
        assert sorted(item.status for item in reminders) == ["canceled", "pending"]
    finally:
        db.close()
