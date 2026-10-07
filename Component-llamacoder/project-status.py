# brain/project.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime


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
    member_ids: List[str] = field(default_factory=list)
    task_ids: List[str] = field(default_factory=list)

    def add_member(self, user_id: str) -> None:
        if user_id in self.member_ids:
            raise ValueError(f"User {user_id} is already a member")
        self.member_ids.append(user_id)

    def add_task(self, task_id: str) -> None:
        self.task_ids.append(task_id)

    def is_complete(self) -> bool:
        return self.status == ProjectStatus.COMPLETED