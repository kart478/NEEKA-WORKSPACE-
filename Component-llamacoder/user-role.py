# brain/user.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
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

    def deactivate(self) -> None:
        self.active = False

    def activate(self) -> None:
        self.active = True