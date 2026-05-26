from fastapi.testclient import TestClient

from services.api.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_list_events(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COMMITBOT_DB_PATH", str(tmp_path / "api.db"))
    client = TestClient(app)

    create_response = client.post(
        "/events",
        json={
            "source": "cli",
            "type": "cli.note",
            "payload": {"message": "from api"},
        },
    )
    list_response = client.get("/events")

    assert create_response.status_code == 200
    assert create_response.json()["payload"]["message"] == "from api"
    assert list_response.status_code == 200
    assert list_response.json()[0]["payload"]["message"] == "from api"
