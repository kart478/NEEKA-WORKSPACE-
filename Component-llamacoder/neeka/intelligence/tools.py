from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from neeka.brain.task import TaskPriority
from neeka.knowledge.context import KnowledgeContextBuilder
from .exceptions import ToolValidationError, UnknownToolError


class EmptyInput(BaseModel):
    pass


class ProjectInput(BaseModel):
    project_id: str
    actor_id: str | None = None


class TaskInput(BaseModel):
    task_id: str


class CreateTaskInput(BaseModel):
    project_id: str
    title: str
    description: str = ""
    creator_id: str
    priority: TaskPriority = TaskPriority.MEDIUM


class UpdateTaskInput(BaseModel):
    task_id: str
    title: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None


class AssignTaskInput(BaseModel):
    task_id: str
    user_id: str
    actor_id: str


class DependencyInput(BaseModel):
    task_id: str
    depends_on_id: str
    actor_id: str


class ActorTaskInput(BaseModel):
    task_id: str
    actor_id: str


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    input_model: type[BaseModel]
    write: bool
    handler: Callable[[Any, dict], Any]


def _model(value: Any) -> dict:
    if hasattr(value, "__dict__"):
        return {key: (item.value if hasattr(item, "value") else item) for key, item in value.__dict__.items()}
    return value


class ToolRegistry:
    def __init__(self, engine) -> None:
        self.engine = engine
        self._tools: dict[str, ToolDefinition] = {}
        self._register_defaults()

    def register(self, definition: ToolDefinition) -> None:
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise UnknownToolError(f"Unknown intelligence tool: {name}")
        return self._tools[name]

    def execute(self, name: str, parameters: dict) -> Any:
        definition = self.get(name)
        try:
            validated = definition.input_model.model_validate(parameters)
        except ValidationError as error:
            raise ToolValidationError(str(error)) from error
        return definition.handler(self.engine, validated.model_dump())

    def definitions(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def _register_defaults(self) -> None:
        self.register(ToolDefinition("get_project", ProjectInput, False, lambda e, p: _model(e.get_project(p["project_id"]))))
        self.register(ToolDefinition("get_projects", EmptyInput, False, lambda e, _p: [_model(x) for x in e.list_projects()]))
        self.register(ToolDefinition("get_task", TaskInput, False, lambda e, p: _model(e.get_task(p["task_id"]))))
        self.register(ToolDefinition("get_tasks", ProjectInput, False, lambda e, p: [_model(x) for x in e.list_tasks(p["project_id"])]))
        self.register(ToolDefinition("get_project_members", ProjectInput, False, lambda e, p: [
            _model(e.get_user(user_id)) for user_id in e.get_project(p["project_id"]).member_ids
        ]))
        self.register(ToolDefinition("get_project_events", ProjectInput, False, lambda e, p: [
            {"event_id": x.id, "event_type": x.event_type.value, "entity_id": x.source_entity,
             "actor_id": x.actor_id, "metadata": x.metadata, "timestamp": x.timestamp.isoformat()}
            for x in e.get_events() if x.source_entity == p["project_id"]
        ]))
        self.register(ToolDefinition("get_project_knowledge", ProjectInput, False, lambda e, p: KnowledgeContextBuilder().build(
            e.get_project_knowledge(p["project_id"], p.get("actor_id") or e.get_project(p["project_id"]).owner_id)
        )))
        self.register(ToolDefinition("get_task_dependencies", TaskInput, False, lambda e, p: [
            _model(e.get_task(task_id)) for task_id in e.get_task(p["task_id"]).dependency_ids
        ]))
        self.register(ToolDefinition("create_task", CreateTaskInput, True, lambda e, p: _model(e.create_task(
            p["title"], p["description"], p["project_id"], p["creator_id"], p["priority"]))))
        self.register(ToolDefinition("update_task", UpdateTaskInput, True, lambda e, p: _model(e.update_task(
            p.pop("task_id"), p.pop("title", None), p.pop("description", None), p.pop("priority", None)))))
        self.register(ToolDefinition("assign_task", AssignTaskInput, True, lambda e, p: (
            e.assign_task(p["task_id"], p["user_id"], p["actor_id"]), _model(e.get_task(p["task_id"]))
        )[1]))
        self.register(ToolDefinition("add_dependency", DependencyInput, True, lambda e, p: (
            e.add_task_dependency(p["task_id"], p["depends_on_id"], p["actor_id"]), _model(e.get_task(p["task_id"]))
        )[1]))
        for name, method in (("start_task", "start_task"), ("complete_task", "complete_task"),
                             ("block_task", "block_task"), ("cancel_task", "cancel_task")):
            self.register(ToolDefinition(name, ActorTaskInput, True, lambda e, p, method=method: (
                getattr(e, method)(p["task_id"], p["actor_id"]), _model(e.get_task(p["task_id"]))
            )[1]))