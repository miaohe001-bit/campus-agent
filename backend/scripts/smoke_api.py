from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib import request
import json


BASE_URL = "http://localhost:8000"
USER_ID = "local-user"


def main() -> None:
    campaign = request_json(
        "POST",
        f"/campaigns",
        {
            "company_name": "Tencent",
            "name": "Tencent 2027 Fall Official Batch",
            "status": "open",
            "target_graduation_year": "2027",
            "position_categories": ["product"],
            "cities": ["Shenzhen"],
            "industries": ["internet"],
            "published_at": date.today().isoformat(),
            "deadline_at": iso_in_days(7),
            "source_name": "seed",
            "source_url": "https://example.com/tencent-2027",
        },
    )

    goal = request_json(
        "PATCH",
        f"/goals?user_id={USER_ID}",
        {
            "graduation_year": "2027",
            "target_positions": ["product"],
            "target_cities": ["Shenzhen"],
            "target_industries": ["internet"],
            "target_companies": [
                {"company_name": "Tencent", "priority": "dream"},
            ],
        },
    )

    application = request_json(
        "POST",
        f"/applications?user_id={USER_ID}",
        {
            "campaign_id": campaign["id"],
            "company_name": "Tencent",
            "position_name": "Product Manager",
            "stage": "submitted",
            "source": "manual",
        },
    )

    todo = request_json(
        "POST",
        f"/todos?user_id={USER_ID}",
        {
            "date": date.today().isoformat(),
            "title": "Prepare Tencent interview",
            "source": "user",
            "estimated_minutes": 45,
            "application_id": application["id"],
            "campaign_id": campaign["id"],
        },
    )

    interview_event = request_json(
        "POST",
        f"/events?user_id={USER_ID}",
        {
            "application_id": application["id"],
            "campaign_id": campaign["id"],
            "event_type": "interview_scheduled",
            "source": "smoke",
            "idempotency_key": f"smoke-interview-{application['id']}",
            "payload": {
                "title": "Tencent Product Manager interview",
                "scheduled_at": iso_in_days(2),
            },
        },
    )

    application_after_interview = request_json(
        "GET",
        f"/applications/{application['id']}?user_id={USER_ID}",
    )
    assert application_after_interview["stage"] == "interview_1"

    schedules = request_json("GET", f"/schedules?user_id={USER_ID}")["items"]
    assert any(item["application_id"] == application["id"] for item in schedules)

    rejected_event = request_json(
        "POST",
        f"/events?user_id={USER_ID}",
        {
            "application_id": application["id"],
            "campaign_id": campaign["id"],
            "event_type": "rejected",
            "source": "smoke",
            "idempotency_key": f"smoke-rejected-{application['id']}",
            "payload": {},
        },
    )

    application_after_rejection = request_json(
        "GET",
        f"/applications/{application['id']}?user_id={USER_ID}",
    )
    assert application_after_rejection["stage"] == "failed"

    todo_after_rejection = request_json("GET", f"/todos/{todo['id']}?user_id={USER_ID}")
    assert todo_after_rejection["status"] == "expired"

    print(
        json.dumps(
            {
                "goal_id": goal["id"],
                "campaign_id": campaign["id"],
                "application_id": application["id"],
                "todo_id": todo["id"],
                "interview_event_id": interview_event["id"],
                "rejected_event_id": rejected_event["id"],
                "schedule_count": len(schedules),
                "application_stage": application_after_rejection["stage"],
                "todo_status": todo_after_rejection["status"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=10) as response:
        body = json.loads(response.read().decode("utf-8"))

    assert body["code"] == 0, body
    return body["data"]


def iso_in_days(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


if __name__ == "__main__":
    main()

