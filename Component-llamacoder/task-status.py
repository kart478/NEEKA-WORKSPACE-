# brain/task.py
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from uuid import uuid4
from datetime import datetime


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
    completed_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    dependency_ids: List[str] = field(default_factory=list)

    def add_dependency(self, task_id: str) -> None:
        if task_id not in self.dependency_ids:
            self.dependency_ids.append(task_id)

    def dependencies_satisfied(self, tasks: dict) -> bool:
        return all(
            tasks[dep_id].status == TaskStatus.COMPLETED
            for dep_id in self.dependency_ids
        )