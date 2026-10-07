from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


@dataclass
class User:
    name: str
    email: str
    role: UserRole = UserRole.MEMBER
    active: bool = True
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def deactivate(self) -> None:
        self.active = False
        self.updated_at = datetime.utcnow()

    def activate(self) -> None:
        self.active = True
        self.updated_at = datetime.utcnow()