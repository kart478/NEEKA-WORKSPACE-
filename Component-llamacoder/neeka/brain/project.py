from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class ProjectStatus(str, Enum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


@dataclass
class Project:
    name: str
    description: str
    owner_id: str
    status: ProjectStatus = ProjectStatus.PLANNED
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    member_ids: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)

    def add_member(self, user_id: str) -> None:
        if user_id in self.member_ids:
            raise ValueError(f"User {user_id} is already a member")
        self.member_ids.append(user_id)
        self.updated_at = datetime.utcnow()

    def add_task(self, task_id: str) -> None:
        if task_id not in self.task_ids:
            self.task_ids.append(task_id)
            self.updated_at = datetime.utcnow()

    def is_complete(self) -> bool:
        return self.status == ProjectStatus.COMPLETED