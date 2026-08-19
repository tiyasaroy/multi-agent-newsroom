from fastapi.testclient import TestClient


def create_story(client: TestClient, source_count: int) -> dict[str, object]:
    story = client.post(
        "/api/v1/stories",
        json={"title": "Transit authority responds to conflicting disruption reports"},
    ).json()
    for index in range(source_count):
        response = client.post(
            f"/api/v1/stories/{story['id']}/sources",
            json={
                "title": f"Independent source report {index + 1}",
                "url": f"https://source-{index + 1}.example/report",
                "publisher": f"Publisher {index + 1}",
                "kind": "article",
                "snapshot_text": (
                    f"Source {index + 1} reports that service changed at 14:00. "
                    "Officials have not yet issued a final timeline."
                ),
            },
        )
        assert response.status_code == 201
    return story


def test_four_agent_workflow_reaches_human_review(client: TestClient) -> None:
    story = create_story(client, source_count=2)

    response = client.post(
        f"/api/v1/stories/{story['id']}/investigations",
        headers={"Idempotency-Key": "review-ready-investigation"},
    )

    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "review"
    assert run["current_stage"] == "human_editor"
    assert run["blocked_reason"] is None
    assert [event["agent"] for event in run["events"]] == [
        "assignment_editor",
        "researcher",
        "reporter",
        "fact_checker",
    ]
    assert len(run["claims"]) == 2
    assert all(claim["verdict"] == "supported" for claim in run["claims"])
    assert all(len(claim["citations"]) == 1 for claim in run["claims"])
    assert run["draft"]["status"] == "human_review"
    assert "[1]" in run["draft"]["body"]


def test_fact_checker_blocks_single_source_story(client: TestClient) -> None:
    story = create_story(client, source_count=1)

    response = client.post(f"/api/v1/stories/{story['id']}/investigations")

    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "blocked"
    assert "two independent sources" in run["blocked_reason"]
    assert run["claims"][0]["verdict"] == "uncorroborated"
    assert run["draft"]["status"] == "blocked"


def test_idempotency_key_returns_original_run(client: TestClient) -> None:
    story = create_story(client, source_count=2)
    path = f"/api/v1/stories/{story['id']}/investigations"
    headers = {"Idempotency-Key": "same-investigation-request"}

    first = client.post(path, headers=headers)
    second = client.post(path, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert len(second.json()["events"]) == 4


def test_investigation_can_be_retrieved(client: TestClient) -> None:
    story = create_story(client, source_count=2)
    created = client.post(f"/api/v1/stories/{story['id']}/investigations").json()

    response = client.get(f"/api/v1/investigations/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_blocked_investigation_can_be_retried_after_new_evidence(client: TestClient) -> None:
    story = create_story(client, source_count=1)
    blocked = client.post(f"/api/v1/stories/{story['id']}/investigations").json()
    assert blocked["status"] == "blocked"

    source_response = client.post(
        f"/api/v1/stories/{story['id']}/sources",
        json={
            "title": "A second independent account",
            "url": "https://second-source.example/account",
            "publisher": "Second Publisher",
            "kind": "article",
            "snapshot_text": "A separate reporter confirms that service changed at 14:00.",
        },
    )
    assert source_response.status_code == 201

    retried = client.post(f"/api/v1/investigations/{blocked['id']}/retry")

    assert retried.status_code == 200
    assert retried.json()["status"] == "review"
    assert retried.json()["id"] != blocked["id"]


def test_completed_investigation_cannot_be_cancelled(client: TestClient) -> None:
    story = create_story(client, source_count=2)
    run = client.post(f"/api/v1/stories/{story['id']}/investigations").json()

    response = client.post(f"/api/v1/investigations/{run['id']}/cancel")

    assert response.status_code == 409


def test_model_shaped_provider_records_usage_telemetry(client: TestClient) -> None:
    story = create_story(client, source_count=2)

    response = client.post(
        f"/api/v1/stories/{story['id']}/investigations?provider=mock"
    )

    assert response.status_code == 201
    run = response.json()
    assert run["provider_requested"] == "mock"
    assert run["provider_used"] == "mock"
    model_events = [event for event in run["events"] if event["provider"] == "mock"]
    assert len(model_events) == 3
    assert all(event["model"] == "mock-newsroom-v1" for event in model_events)
    assert all(event["input_tokens"] == 100 for event in model_events)
    assert run["draft"]["status"] == "human_review"


def test_event_stream_replays_agent_activity(client: TestClient) -> None:
    story = create_story(client, source_count=2)
    run = client.post(f"/api/v1/stories/{story['id']}/investigations").json()

    response = client.get(f"/api/v1/investigations/{run['id']}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.count("event: agent_event") == 4
    assert 'event: complete\ndata: {"status":"review"}' in response.text


def test_human_editor_can_approve_review_ready_draft(client: TestClient) -> None:
    story = create_story(client, source_count=2)
    run = client.post(f"/api/v1/stories/{story['id']}/investigations").json()

    response = client.post(
        f"/api/v1/investigations/{run['id']}/approve",
        json={"editor_name": "Maya Chen", "note": "Evidence and attribution verified."},
    )

    assert response.status_code == 200
    approved = response.json()
    assert approved["status"] == "approved"
    assert approved["current_stage"] is None
    assert approved["draft"]["status"] == "approved"
    assert approved["editorial_decisions"] == [
        {
            "id": approved["editorial_decisions"][0]["id"],
            "action": "approved",
            "editor_name": "Maya Chen",
            "note": "Evidence and attribution verified.",
            "created_at": approved["editorial_decisions"][0]["created_at"],
        }
    ]
    assert client.get(f"/api/v1/stories/{story['id']}").json()["status"] == "approved"


def test_human_editor_can_request_revision_with_audit_note(client: TestClient) -> None:
    story = create_story(client, source_count=2)
    run = client.post(f"/api/v1/stories/{story['id']}/investigations").json()

    response = client.post(
        f"/api/v1/investigations/{run['id']}/request-revision",
        json={"editor_name": "Maya Chen", "note": "Clarify the restoration timeline."},
    )

    assert response.status_code == 200
    revised = response.json()
    assert revised["status"] == "revision_requested"
    assert revised["current_stage"] == "reporter"
    assert revised["draft"]["status"] == "revision_requested"
    assert revised["blocked_reason"] == "Clarify the restoration timeline."
    assert revised["editorial_decisions"][0]["action"] == "revision_requested"
    assert client.get(f"/api/v1/stories/{story['id']}").json()["status"] == "developing"


def test_editorial_decision_cannot_be_recorded_twice(client: TestClient) -> None:
    story = create_story(client, source_count=2)
    run = client.post(f"/api/v1/stories/{story['id']}/investigations").json()
    path = f"/api/v1/investigations/{run['id']}/approve"
    payload = {"editor_name": "Maya Chen"}

    assert client.post(path, json=payload).status_code == 200
    assert client.post(path, json=payload).status_code == 409
