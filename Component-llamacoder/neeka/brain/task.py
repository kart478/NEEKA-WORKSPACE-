from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class TaskStatus(str, Enum):
    TODO = "TODO"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Task:
    title: str
    description: str
    project_id: str
    creator_id: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    assigned_to: str | None = None
    dependency_ids: list[str] = field(default_factory=list)

    def add_dependency(self, task_id: str) -> None:
        if task_id not in self.dependency_ids:
            self.dependency_ids.append(task_id)
            self.updated_at = datetime.utcnow()

    def dependencies_satisfied(self, tasks: dict[str, "Task"]) -> bool:
        return all(tasks[dep_id].status == TaskStatus.COMPLETED for dep_id in self.dependency_ids)