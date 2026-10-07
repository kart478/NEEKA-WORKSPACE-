from typing import Any

from pydantic import BaseModel, Field

from .audit import AIAuditor
from .context import ContextBuilder
from .exceptions import IntelligenceLoopError, InvalidAIResponseError
from .permissions import PermissionMode, authorize
from .planner import Planner
from .providers.base import AIProvider
from .providers.mock import MockAIProvider
from .tools import ToolRegistry


class StructuredAction(BaseModel):
    action: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class IntelligenceGateway:
    """The only intelligence entry point; all state changes go through Brain tools."""

    def __init__(self, engine, provider: AIProvider | None = None, audit_repository=None, max_actions: int = 10) -> None:
        self.engine = engine
        self.provider = provider or MockAIProvider()
        self.context_builder = ContextBuilder(engine)
        self.tools = ToolRegistry(engine)
        self.planner = Planner(self.provider)
        repository = audit_repository or engine.ai_audit_repository
        self.auditor = AIAuditor(repository)
        self.max_actions = max_actions

    def analyze(self, project_id: str, mode: PermissionMode = PermissionMode.READ_ONLY) -> dict:
        context = self.context_builder.project(project_id)
        try:
            response = self.provider.analyze(context.as_dict())
            result = {"provider": self.provider.provider_name, "project_id": project_id,
                      "analysis": response.data, "content": response.content}
            self.auditor.record(self.provider.provider_name, "analyze", mode.value, True, project_id=project_id)
            return result
        except Exception as error:
            self.auditor.record(self.provider.provider_name, "analyze", mode.value, False,
                                error=str(error), project_id=project_id)
            raise

    def plan(self, project_id: str, goal: str, mode: PermissionMode = PermissionMode.READ_ONLY) -> dict:
        context = self.context_builder.project(project_id)
        try:
            result = self.planner.plan(goal, context.as_dict()).model_dump()
            self.auditor.record(self.provider.provider_name, "plan", mode.value, True, project_id=project_id)
            return result
        except Exception as error:
            self.auditor.record(self.provider.provider_name, "plan", mode.value, False,
                                error=str(error), project_id=project_id)
            raise

    def execute_action(self, request: StructuredAction, mode: PermissionMode,
                       approved: bool = False, depth: int = 0) -> dict:
        if depth > self.max_actions:
            raise IntelligenceLoopError(f"Intelligence action depth exceeded {self.max_actions}")
        project_id = request.parameters.get("project_id")
        task_id = request.parameters.get("task_id")
        try:
            tool = self.tools.get(request.action)
            authorize(mode, tool.write, approved)
            result = self.tools.execute(request.action, request.parameters)
            self.auditor.record(self.provider.provider_name, "action", mode.value, True,
                                action=request.action, parameters=request.parameters,
                                project_id=project_id, task_id=task_id)
            return {"action": request.action, "success": True, "result": result}
        except Exception as error:
            self.auditor.record(self.provider.provider_name, "action", mode.value, False,
                                action=request.action, parameters=request.parameters,
                                error=str(error), project_id=project_id, task_id=task_id)
            raise

    def audit(self) -> list[dict]:
        return self.auditor.list()