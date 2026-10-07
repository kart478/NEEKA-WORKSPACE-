from fastapi.testclient import TestClient

from neeka.api import create_app


def make_client(tmp_path):
    return TestClient(create_app(tmp_path / "api.db"))


def test_health_and_openapi(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/health").json() == {"status": "ok", "service": "neeka"}
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    assert "/api/v1/tasks/{task_id}/complete" in client.get("/openapi.json").json()["paths"]


def test_api_controls_workflow_and_persists_after_restart(tmp_path):
    client = make_client(tmp_path)
    owner = client.post("/api/v1/users", json={"name": "Owner", "email": "owner@example.com", "role": "MANAGER"}).json()
    john = client.post("/api/v1/users", json={"name": "John", "email": "john@example.com"}).json()
    sarah = client.post("/api/v1/users", json={"name": "Sarah", "email": "sarah@example.com"}).json()
    project = client.post("/api/v1/projects", json={"name": "Build School Report", "owner_id": owner["id"]}).json()

    assert client.post(f"/api/v1/projects/{project['id']}/members", json={
        "user_id": john["id"], "actor_id": owner["id"],
    }).status_code == 204
    assert client.post(f"/api/v1/projects/{project['id']}/members", json={
        "user_id": sarah["id"], "actor_id": owner["id"],
    }).status_code == 204
    task_a = client.post(f"/api/v1/projects/{project['id']}/tasks", json={
        "title": "Collect teacher information", "creator_id": owner["id"],
    }).json()
    task_b = client.post(f"/api/v1/projects/{project['id']}/tasks", json={
        "title": "Compile report", "creator_id": owner["id"],
    }).json()
    assert client.post(f"/api/v1/tasks/{task_b['id']}/dependencies", json={
        "depends_on_id": task_a["id"], "actor_id": owner["id"],
    }).status_code == 204
    assert client.post(f"/api/v1/tasks/{task_a['id']}/assign", json={
        "user_id": john["id"], "actor_id": owner["id"],
    }).status_code == 200
    assert client.post(f"/api/v1/tasks/{task_a['id']}/start", json={"actor_id": john["id"]}).json()["status"] == "IN_PROGRESS"
    assert client.post(f"/api/v1/tasks/{task_a['id']}/complete", json={"actor_id": john["id"]}).json()["status"] == "COMPLETED"
    assert client.get(f"/api/v1/tasks/{task_b['id']}").json()["status"] == "READY"
    assert client.post(f"/api/v1/tasks/{task_b['id']}/assign", json={
        "user_id": sarah["id"], "actor_id": owner["id"],
    }).status_code == 200

    events = client.get("/api/v1/events").json()
    assert any(event["event_type"] == "TASK_COMPLETED" for event in events)
    assert any(event["event_type"] == "TASK_READY" for event in events)
    executions = client.get("/api/v1/automation/executions").json()
    assert any(execution["status"] == "SUCCESS" for execution in executions)

    restarted = make_client(tmp_path)
    assert restarted.get(f"/api/v1/tasks/{task_a['id']}").json()["status"] == "COMPLETED"
    assert len(restarted.get(f"/api/v1/projects/{project['id']}/events").json()) >= 5


def test_api_errors_and_validation(tmp_path):
    client = make_client(tmp_path)
    missing = client.get("/api/v1/tasks/missing")
    assert missing.status_code == 404
    assert missing.json()["error"] == "task_not_found"
    invalid = client.post("/api/v1/users", json={"email": "missing-name@example.com"})
    assert invalid.status_code == 422
    assert client.get("/api/v1/workflows/unknown").status_code == 404


def test_api_rejects_circular_dependency(tmp_path):
    client = make_client(tmp_path)
    owner = client.post("/api/v1/users", json={"name": "Owner", "email": "owner@example.com"}).json()
    project = client.post("/api/v1/projects", json={"name": "Project", "owner_id": owner["id"]}).json()
    task_a = client.post(f"/api/v1/projects/{project['id']}/tasks", json={"title": "A", "creator_id": owner["id"]}).json()
    task_b = client.post(f"/api/v1/projects/{project['id']}/tasks", json={"title": "B", "creator_id": owner["id"]}).json()
    assert client.post(f"/api/v1/tasks/{task_a['id']}/dependencies", json={
        "depends_on_id": task_b["id"], "actor_id": owner["id"],
    }).status_code == 204
    circular = client.post(f"/api/v1/tasks/{task_b['id']}/dependencies", json={
        "depends_on_id": task_a["id"], "actor_id": owner["id"],
    })
    assert circular.status_code == 409
    assert circular.json()["error"] == "circular_dependency"