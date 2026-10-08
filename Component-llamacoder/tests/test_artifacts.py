from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from neeka import NEEKAEngine
from neeka.api import create_app
from neeka.artifacts.artifact import ArtifactType
from neeka.artifacts.exceptions import ArtifactPermissionError, ArtifactValidationError
from neeka.artifacts.relationships import ArtifactRole
from neeka.brain.event import EventType


def setup_engine(tmp_path, max_size=50 * 1024 * 1024):
    engine = NEEKAEngine(tmp_path / "artifacts.db", artifact_max_size=max_size)
    owner = engine.create_user("Owner", "owner@example.com")
    outsider = engine.create_user("Outsider", "outsider@example.com")
    project = engine.create_project("Artifacts", "Outputs", owner.id)
    task = engine.create_task("Prepare report", "", project.id, owner.id)
    return engine, owner, outsider, project, task


def test_artifact_upload_checksum_download_version_restore_and_restart(tmp_path):
    engine, owner, _, project, _ = setup_engine(tmp_path)
    artifact = engine.create_artifact(project.id, "report.txt", "Report", ArtifactType.DOCUMENT,
                                      "text/plain", BytesIO(b"version one"), owner.id)
    assert artifact.checksum == "".join(__import__("hashlib").sha256(b"version one").hexdigest())
    with engine.read_artifact(artifact.id, owner.id) as stream:
        assert stream.read() == b"version one"
    engine.create_artifact_version(artifact.id, BytesIO(b"version two"), owner.id)
    assert [item.version_number for item in engine.artifact_versions(artifact.id, owner.id)] == [1, 2]
    engine.restore_artifact_version(artifact.id, 1, owner.id)
    with engine.read_artifact(artifact.id, owner.id) as stream:
        assert stream.read() == b"version one"
    restarted = NEEKAEngine(tmp_path / "artifacts.db")
    assert restarted.get_artifact(artifact.id, owner.id).current_version == 1
    assert any(event.event_type == EventType.ARTIFACT_VERSION_CREATED for event in restarted.get_events())


def test_artifact_permissions_path_safety_duplicates_and_task_relationship(tmp_path):
    engine, owner, outsider, project, task = setup_engine(tmp_path)
    artifact = engine.create_artifact(project.id, "data.csv", "", ArtifactType.DATA, "text/csv", BytesIO(b"a,b"), owner.id)
    duplicate = engine.create_artifact(project.id, "copy.csv", "", ArtifactType.DATA, "text/csv", BytesIO(b"a,b"), owner.id)
    assert duplicate.checksum == artifact.checksum
    assert len(engine.artifacts.duplicates(project.id, artifact.checksum, owner.id)) == 2
    engine.attach_artifact(artifact.id, "task", task.id, ArtifactRole.INPUT, owner.id)
    assert engine.task_artifacts(task.id, owner.id)[0].id == artifact.id
    with pytest.raises(ArtifactPermissionError):
        engine.get_artifact(artifact.id, outsider.id)
    with pytest.raises(ArtifactValidationError):
        engine.create_artifact(project.id, "../unsafe.txt", "", ArtifactType.DOCUMENT, "text/plain", BytesIO(b"x"), owner.id)


def test_artifact_size_limit_and_soft_delete(tmp_path):
    engine, owner, _, project, _ = setup_engine(tmp_path, max_size=3)
    with pytest.raises(ArtifactValidationError):
        engine.create_artifact(project.id, "large.bin", "", ArtifactType.OTHER, "application/octet-stream", BytesIO(b"1234"), owner.id)
    engine.artifact_max_size = 50
    artifact = engine.create_artifact(project.id, "small.bin", "", ArtifactType.OTHER, "application/octet-stream", BytesIO(b"12"), owner.id)
    engine.delete_artifact(artifact.id, owner.id)
    assert engine.get_artifact(artifact.id, owner.id).status.value == "DELETED"
    with pytest.raises(Exception):
        engine.read_artifact(artifact.id, owner.id)


def test_artifact_api_upload_download_and_task_attachment(tmp_path):
    client = TestClient(create_app(tmp_path / "api.db"))
    owner = client.post("/api/v1/users", json={"name": "Owner", "email": "owner@example.com"}).json()
    project = client.post("/api/v1/projects", json={"name": "Project", "owner_id": owner["id"]}).json()
    task = client.post(f"/api/v1/projects/{project['id']}/tasks", json={
        "title": "Task", "creator_id": owner["id"],
    }).json()
    response = client.post(f"/api/v1/projects/{project['id']}/artifacts", data={"actor_id": owner["id"]}, files={
        "file": ("report.txt", b"hello artifact", "text/plain"),
    })
    assert response.status_code == 201
    artifact = response.json()
    download = client.get(f"/api/v1/artifacts/{artifact['id']}/download", params={"actor_id": owner["id"]})
    assert download.status_code == 200 and download.content == b"hello artifact"
    attached = client.post(f"/api/v1/artifacts/{artifact['id']}/relationships", json={
        "target_type": "task", "target_id": task["id"], "role": "OUTPUT", "actor_id": owner["id"],
    })
    assert attached.status_code == 200
    assert client.get(f"/api/v1/tasks/{task['id']}/artifacts", params={"actor_id": owner["id"]}).json()[0]["id"] == artifact["id"]
