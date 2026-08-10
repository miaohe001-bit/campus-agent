from fastapi.testclient import TestClient

from app.main import create_app


def test_health_response_format() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "message": "success",
        "data": {"status": "ok"},
    }


def test_local_frontend_cors_preflight() -> None:
    client = TestClient(create_app())

    response = client.options(
        "/campaigns?include_closed=true",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
