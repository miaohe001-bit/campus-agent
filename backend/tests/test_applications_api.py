from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def test_campaign_application_creation_is_idempotent() -> None:
    client = TestClient(create_app())
    user_id = f"test-application-{uuid4()}"
    campaign = client.post(
        "/campaigns",
        json={
            "company_name": "测试公司",
            "name": "2027 届校园招聘",
            "status": "open",
            "target_graduation_year": "2027",
        },
    ).json()["data"]
    payload = {
        "campaign_id": campaign["id"],
        "company_name": "不会采用的公司名",
        "position_name": " 产品经理 ",
        "stage": "submitted",
        "source": "radar",
    }

    first = client.post(f"/applications?user_id={user_id}", json=payload)
    second = client.post(f"/applications?user_id={user_id}", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    assert first.json()["data"]["company_name"] == "测试公司"
    applications = client.get(f"/applications?user_id={user_id}").json()["data"]["items"]
    assert len(applications) == 1


def test_campaign_exposes_application_url_from_event_payload() -> None:
    client = TestClient(create_app())
    user_id = f"test-campaign-link-{uuid4()}"
    campaign = client.post(
        "/campaigns",
        json={"company_name": "测试公司", "name": "2027 秋招", "status": "open"},
    ).json()["data"]
    client.post(
        f"/events?user_id={user_id}",
        json={
            "campaign_id": campaign["id"],
            "event_type": "deadline_updated",
            "source": "official_wechat",
            "payload": {"application_url": "https://jobs.example.com/apply"},
        },
    )

    detail = client.get(f"/campaigns/{campaign['id']}").json()["data"]
    assert detail["application_url"] == "https://jobs.example.com/apply"
