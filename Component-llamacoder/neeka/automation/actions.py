from dataclasses import dataclass
from typing import Protocol

from neeka.brain.event import EventType
from neeka.brain.task import TaskStatus


class AutomationAction(Protocol):
    def execute(self, engine, event) -> None: ...


@dataclass(frozen=True)
class UnlockDependentTasksAction:
    """Move eligible blocked dependents to READY and emit TASK_READY."""

    def execute(self, engine, event) -> None:
        engine._unlock_dependent_tasks(event.source_entity, event.actor_id, event.metadata)


@dataclass(frozen=True)
class ChangeTaskStatusAction:
    task_id: str
    status: TaskStatus

    def execute(self, engine, event) -> None:
        task = engine.get_task(self.task_id)
        engine.transition_task(task.id, self.status, event.actor_id)


@dataclass(frozen=True)
class GenerateEventAction:
    event_type: EventType
    entity_id: str

    def execute(self, engine, event) -> None:
        depth = int(event.metadata.get("_automation_depth", 0)) + 1
        engine._emit_event(
            self.event_type,
            self.entity_id,
            event.actor_id,
            {"automation": True, "_automation_depth": depth},
        )


@dataclass(frozen=True)
class AssignTaskAction:
    task_id: str
    user_id: str

    def execute(self, engine, event) -> None:
        engine.assign_task(self.task_id, self.user_id, event.actor_id)


@dataclass(frozen=True)
class UnassignTaskAction:
    task_id: str

    def execute(self, engine, event) -> None:
        task = engine.get_task(self.task_id)
        task.assigned_to = None
        task.updated_at = engine.utcnow()
        engine.tasks.save(task)


@dataclass(frozen=True)
class AddDependencyAction:
    task_id: str
    depends_on_id: str

    def execute(self, engine, event) -> None:
        engine.add_task_dependency(self.task_id, self.depends_on_id, event.actor_id)


@dataclass(frozen=True)
class CreateTaskAction:
    title: str
    description: str
    project_id: str
    creator_id: str

    def execute(self, engine, event):
        return engine.create_task(self.title, self.description, self.project_id, self.creator_id)