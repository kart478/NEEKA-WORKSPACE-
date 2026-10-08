import pytest
from fastapi.testclient import TestClient

from neeka import NEEKAEngine
from neeka.api import create_app
from neeka.brain.event import EventType
from neeka.intelligence.context import ContextBuilder
from neeka.knowledge.decision import Decision, DecisionStatus
from neeka.knowledge.document import Document
from neeka.knowledge.exceptions import KnowledgePermissionError
from neeka.knowledge.note import Note
from neeka.knowledge.reference import Reference
from neeka.knowledge.requirement import Requirement


def setup_engine(tmp_path):
    engine = NEEKAEngine(tmp_path / "knowledge.db")
    owner = engine.create_user("Owner", "owner@example.com")
    member = engine.create_user("Member", "member@example.com")
    outsider = engine.create_user("Outsider", "outsider@example.com")
    project = engine.create_project("Knowledge Project", "Goal", owner.id)
    engine.add_project_member(project.id, member.id, owner.id)
    return engine, owner, member, outsider, project


def test_document_versions_and_restart(tmp_path):
    engine, owner, _, _, project = setup_engine(tmp_path)
    document = engine.create_document(Document(project.id, "Architecture", "", "v1"), owner.id)
    engine.update_document(document.id, owner.id, content="v2")
    assert engine.get_document(document.id, owner.id).version == 2
    assert [version.content for version in engine.document_versions(document.id, owner.id)] == ["v1", "v2"]
    restarted = NEEKAEngine(tmp_path / "knowledge.db")
    assert restarted.get_document(document.id, owner.id).content == "v2"


def test_knowledge_entities_search_tags_relationships_and_context(tmp_path):
    engine, owner, _, _, project = setup_engine(tmp_path)
    document = engine.create_document(Document(project.id, "FastAPI Architecture", "API", "FastAPI selected"), owner.id)
    requirement = engine.create_requirement(Requirement(project.id, "Desktop app", "", owner.id), owner.id)
    decision = engine.create_decision(Decision(project.id, "API framework", "Use FastAPI", "Simple API", owner.id), owner.id)
    engine.create_note(Note(project.id, "Meeting", "FastAPI discussed", owner.id, ["api", "architecture"]), owner.id)
    engine.create_reference(Reference(project.id, "FastAPI docs", "https://fastapi.tiangolo.com", "Docs", "official", owner.id), owner.id)
    engine.add_knowledge_relationship(project.id, owner.id, "requirement", requirement.id, "IMPLEMENTS", "task", "task-1")
    results = engine.search_knowledge(project.id, owner.id, "FastAPI")
    assert {item["type"] for item in results} == {"DOCUMENT", "DECISION", "NOTE", "REFERENCE"}
    assert engine.knowledge_repository.relationships("requirement", requirement.id)[0]["target_id"] == "task-1"
    context = ContextBuilder(engine).project(project.id)
    assert context.knowledge["documents"][0]["id"] == document.id
    assert context.knowledge["decisions"][0]["decision"] == "Use FastAPI"


def test_decision_lifecycle_and_events(tmp_path):
    engine, owner, _, _, project = setup_engine(tmp_path)
    decision = engine.create_decision(Decision(project.id, "Choice", "A", "Reason", owner.id), owner.id)
    engine.update_decision(decision.id, project.id, owner.id, status=DecisionStatus.ACCEPTED)
    assert engine.knowledge_repository.list_decisions(project.id)[0].status == DecisionStatus.ACCEPTED
    assert any(event.event_type == EventType.DECISION_ACCEPTED for event in engine.get_events())


def test_knowledge_permissions(tmp_path):
    engine, owner, _, outsider, project = setup_engine(tmp_path)
    engine.create_note(Note(project.id, "Private", "content", owner.id), owner.id)
    with pytest.raises(KnowledgePermissionError):
        engine.get_project_knowledge(project.id, outsider.id)


def test_knowledge_api(tmp_path):
    client = TestClient(create_app(tmp_path / "api.db"))
    owner = client.post("/api/v1/users", json={"name": "Owner", "email": "owner@example.com"}).json()
    project = client.post("/api/v1/projects", json={"name": "Project", "owner_id": owner["id"]}).json()
    document = client.post(f"/api/v1/projects/{project['id']}/documents", json={
        "title": "Spec", "content": "SQLite", "actor_id": owner["id"],
    })
    assert document.status_code == 201
    assert client.get(f"/api/v1/projects/{project['id']}/documents", params={"actor_id": owner["id"]}).status_code == 200
    knowledge = client.get(f"/api/v1/projects/{project['id']}/knowledge", params={"actor_id": owner["id"]})
    assert knowledge.status_code == 200
    assert knowledge.json()["documents"][0]["title"] == "Spec"
    assert client.get(f"/api/v1/projects/{project['id']}/knowledge/search", params={
        "actor_id": owner["id"], "keyword": "SQLite",
    }).json()[0]["type"] == "DOCUMENT"
