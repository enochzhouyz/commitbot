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


def test_full_stack_baseline_endpoints(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COMMITBOT_DB_PATH", str(tmp_path / "fullstack.db"))
    client = TestClient(app)

    client.post(
        "/events",
        json={
            "source": "cli",
            "type": "cli.note",
            "payload": {"message": "worked on frontend"},
        },
    )
    goal_response = client.post("/goals", json={"title": "Improve AI infra", "type": "skill"})
    plan_response = client.post(
        "/plans",
        json={"title": "Quarterly direction", "horizon": "quarterly", "narrative": "Ship baseline"},
    )
    ask_response = client.post("/agent/ask", json={"question": "What frontend work happened?"})

    assert goal_response.status_code == 200
    assert plan_response.status_code == 200
    assert ask_response.status_code == 200
    assert "captured traces" in ask_response.json()["answer"]
    assert client.get("/timeline").status_code == 200
    assert client.get("/goals").json()[0]["title"] == "Improve AI infra"
    assert client.get("/plans").json()[0]["title"] == "Quarterly direction"


def test_static_index_served() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Commitbot" in response.text


def test_git_collector_endpoint(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COMMITBOT_DB_PATH", str(tmp_path / "collector.db"))
    client = TestClient(app)

    response = client.post("/collectors/git")

    assert response.status_code == 200
    assert response.json()["captured"] >= 1
