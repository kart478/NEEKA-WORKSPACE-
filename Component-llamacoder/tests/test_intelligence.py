import pytest
from fastapi.testclient import TestClient

from neeka import NEEKAEngine
from neeka.api import create_app
from neeka.intelligence.context import ContextBuilder
from neeka.intelligence.exceptions import (
    ApprovalRequiredError, UnauthorizedIntelligenceAction, UnknownToolError,
)
from neeka.intelligence.gateway import IntelligenceGateway, StructuredAction
from neeka.intelligence.permissions import PermissionMode
from neeka.intelligence.providers.mock import MockAIProvider
from neeka.brain.task import TaskStatus


def setup_engine(tmp_path):
    engine = NEEKAEngine(tmp_path / "intelligence.db")
    owner = engine.create_user("Owner", "owner@example.com")
    project = engine.create_project("Project", "Goal", owner.id)
    return engine, owner, project


def test_mock_provider_and_bounded_context(tmp_path):
    engine, _, project = setup_engine(tmp_path)
    context = ContextBuilder(engine, recent_event_limit=1).project(project.id)
    assert context.project_id == project.id
    assert len(context.recent_events) <= 1
    response = MockAIProvider().analyze(context.as_dict())
    assert response.data["summary"].startswith("Project")


def test_planner_returns_structured_plan(tmp_path):
    engine, _, project = setup_engine(tmp_path)
    plan = IntelligenceGateway(engine).plan(project.id, "Launch website")
    assert plan["goal"] == "Launch website"
    assert len(plan["steps"]) >= 1


def test_permission_modes_and_controlled_action_execution(tmp_path):
    engine, owner, project = setup_engine(tmp_path)
    gateway = IntelligenceGateway(engine)
    action = StructuredAction(action="create_task", parameters={
        "project_id": project.id, "title": "Build API", "creator_id": owner.id,
    })
    with pytest.raises(UnauthorizedIntelligenceAction):
        gateway.execute_action(action, PermissionMode.READ_ONLY)
    with pytest.raises(ApprovalRequiredError):
        gateway.execute_action(action, PermissionMode.ASSISTED)
    result = gateway.execute_action(action, PermissionMode.ASSISTED, approved=True)
    assert result["success"] is True
    assert engine.list_tasks(project.id)[0].title == "Build API"
    assert any(record["operation"] == "action" and record["success"] for record in gateway.audit())


def test_tools_validate_unknown_and_malformed_calls(tmp_path):
    engine, _, _ = setup_engine(tmp_path)
    gateway = IntelligenceGateway(engine)
    with pytest.raises(UnknownToolError):
        gateway.execute_action(StructuredAction(action="drop_database"), PermissionMode.READ_ONLY)
    with pytest.raises(Exception):
        gateway.execute_action(StructuredAction(action="get_task", parameters={}), PermissionMode.READ_ONLY)


def test_autonomous_action_uses_brain_workflow(tmp_path):
    engine, owner, project = setup_engine(tmp_path)
    task = engine.create_task("Task", "", project.id, owner.id)
    gateway = IntelligenceGateway(engine)
    result = gateway.execute_action(
        StructuredAction(action="start_task", parameters={"task_id": task.id, "actor_id": owner.id}),
        PermissionMode.AUTONOMOUS,
    )
    assert result["success"] is True
    assert engine.get_task(task.id).status == TaskStatus.IN_PROGRESS


def test_audit_survives_restart(tmp_path):
    engine, _, project = setup_engine(tmp_path)
    IntelligenceGateway(engine).analyze(project.id)
    restarted = NEEKAEngine(tmp_path / "intelligence.db")
    assert any(record["operation"] == "analyze" for record in IntelligenceGateway(restarted).audit())


def test_intelligence_api_endpoints(tmp_path):
    client = TestClient(create_app(tmp_path / "api.db"))
    owner = client.post("/api/v1/users", json={"name": "Owner", "email": "owner@example.com"}).json()
    project = client.post("/api/v1/projects", json={"name": "Project", "owner_id": owner["id"]}).json()
    analysis = client.post("/api/v1/intelligence/analyze", json={"project_id": project["id"]})
    assert analysis.status_code == 200
    plan = client.post("/api/v1/intelligence/plan", json={
        "project_id": project["id"], "goal": "Ship release",
    })
    assert plan.status_code == 200
    action = client.post("/api/v1/intelligence/action", json={
        "action": "create_task", "mode": "AUTONOMOUS", "parameters": {
            "project_id": project["id"], "title": "Release", "creator_id": owner["id"],
        },
    })
    assert action.status_code == 200
    assert len(client.get("/api/v1/intelligence/audit").json()) >= 3