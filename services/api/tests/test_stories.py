from fastapi.testclient import TestClient


def test_story_source_workflow(client: TestClient) -> None:
    story_response = client.post(
        "/api/v1/stories",
        json={
            "title": "Conflicting reports emerge from the city centre",
            "summary": "The assignment desk is gathering independent accounts.",
        },
    )
    assert story_response.status_code == 201
    story = story_response.json()
    assert story["status"] == "developing"

    source_response = client.post(
        f"/api/v1/stories/{story['id']}/sources",
        json={
            "title": "Eyewitness notes submitted to the assignment desk",
            "kind": "manual",
            "snapshot_text": (
                "The witness described the event and provided a precise local timestamp."
            ),
        },
    )
    assert source_response.status_code == 201
    assert source_response.json()["story_id"] == story["id"]

    detail_response = client.get(f"/api/v1/stories/{story['id']}")
    assert detail_response.status_code == 200
    assert len(detail_response.json()["sources"]) == 1

    list_response = client.get("/api/v1/stories?story_status=developing")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [story["id"]]


def test_web_source_requires_url(client: TestClient) -> None:
    story = client.post("/api/v1/stories", json={"title": "A developing verified story"}).json()

    response = client.post(
        f"/api/v1/stories/{story['id']}/sources",
        json={
            "title": "Published report without a URL",
            "kind": "article",
            "snapshot_text": (
                "This content is long enough to pass the minimum snapshot requirement."
            ),
        },
    )

    assert response.status_code == 422


def test_missing_story_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/stories/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
