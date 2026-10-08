from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from neeka.brain.engine import NEEKAEngine
from neeka.knowledge.project_knowledge import ProjectKnowledge


@dataclass(frozen=True)
class TaskContext:
    id: str
    title: str
    description: str
    status: str
    priority: str
    assigned_to: str | None
    dependencies: list[str]


@dataclass(frozen=True)
class ProjectContext:
    project_id: str
    name: str
    description: str
    status: str
    owner_id: str
    member_ids: list[str]
    tasks: list[TaskContext]
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    knowledge: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContextBuilder:
    """Builds bounded, deliberate context through the Brain query surface."""

    def __init__(self, engine: NEEKAEngine, recent_event_limit: int = 20) -> None:
        self.engine = engine
        self.recent_event_limit = recent_event_limit

    def project(self, project_id: str) -> ProjectContext:
        project = self.engine.get_project(project_id)
        tasks = [
            TaskContext(
                id=task.id, title=task.title, description=task.description,
                status=task.status.value, priority=task.priority.value,
                assigned_to=task.assigned_to, dependencies=list(task.dependency_ids),
            )
            for task in self.engine.get_project_tasks(project_id)
        ]
        events = [
            {"event_type": event.event_type.value, "entity_id": event.source_entity,
             "actor_id": event.actor_id, "timestamp": event.timestamp.isoformat(),
             "metadata": event.metadata}
            for event in self.engine.get_events()
            if event.source_entity == project_id or event.source_entity in project.task_ids
        ][-self.recent_event_limit:]
        knowledge = self.engine.get_project_knowledge(project_id, project.owner_id)
        return ProjectContext(
            project_id=project.id, name=project.name, description=project.description,
            status=project.status.value, owner_id=project.owner_id,
            member_ids=list(project.member_ids), tasks=tasks, recent_events=events,
            knowledge=self._knowledge_dict(knowledge),
        )

    @staticmethod
    def _knowledge_dict(knowledge: ProjectKnowledge) -> dict[str, list[dict[str, Any]]]:
        def serialize(items: list[Any]) -> list[dict[str, Any]]:
            return [{key: (value.value if hasattr(value, "value") else value)
                     for key, value in asdict(item).items()} for item in items]

        return {
            "documents": serialize(knowledge.documents),
            "requirements": serialize(knowledge.requirements),
            "decisions": serialize(knowledge.decisions),
            "notes": serialize(knowledge.notes),
            "references": serialize(knowledge.references),
        }