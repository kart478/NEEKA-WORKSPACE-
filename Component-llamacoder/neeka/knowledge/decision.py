from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class DecisionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


@dataclass
class Decision:
    project_id: str
    title: str
    decision: str
    reason: str
    created_by: str
    alternatives_considered: list[str] = field(default_factory=list)
    status: DecisionStatus = DecisionStatus.PROPOSED
    superseded_by: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
