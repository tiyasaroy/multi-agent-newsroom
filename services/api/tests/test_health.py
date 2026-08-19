from fastapi.testclient import TestClient

from newsroom_api.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "newsroom-api",
        "environment": "development",
    }


def test_newsroom_requires_human_publication_gate() -> None:
    response = client.get("/api/v1/newsroom")

    assert response.status_code == 200
    assert response.json()["publication_gate"] == "human_required"
