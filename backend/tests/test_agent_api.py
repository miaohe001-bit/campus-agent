from fastapi.testclient import TestClient

from app.main import create_app


def test_scheduler_status_shape() -> None:
    client = TestClient(create_app())

    response = client.get("/agent/scheduler")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert "jobs" in body["data"]
