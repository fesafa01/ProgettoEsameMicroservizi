from fastapi.testclient import TestClient

from kv.main import app


client = TestClient(app)


def test_examples_endpoint_lists_many_examples():
    response = client.get("/api/v1/examples")
    assert response.status_code == 200
    payload = response.json()
    assert "examples" in payload
    assert len(payload["examples"]) >= 10
    assert "01_valid_baseline.json" in payload["examples"]


def test_load_example_replaces_active_snapshot():
    response = client.post("/api/v1/load-example", params={"name": "05_missing_domain.json"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "loaded"
    assert payload["snapshot_id"] == "kb-demo-2026-02-16-005"

    knowledge = client.get("/api/v1/knowledge")
    assert knowledge.status_code == 200
    kb = knowledge.json()
    assert kb["snapshot_id"] == "kb-demo-2026-02-16-005"

