from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class EventType(str, Enum):
    PROJECT_CREATED = "PROJECT_CREATED"
    TASK_CREATED = "TASK_CREATED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_STARTED = "TASK_STARTED"
    TASK_BLOCKED = "TASK_BLOCKED"
    TASK_READY = "TASK_READY"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_CANCELLED = "TASK_CANCELLED"
    USER_ADDED_TO_PROJECT = "USER_ADDED_TO_PROJECT"
    USER_REMOVED_FROM_PROJECT = "USER_REMOVED_FROM_PROJECT"
    DOCUMENT_CREATED = "DOCUMENT_CREATED"
    DOCUMENT_UPDATED = "DOCUMENT_UPDATED"
    DOCUMENT_VERSION_CREATED = "DOCUMENT_VERSION_CREATED"
    REQUIREMENT_CREATED = "REQUIREMENT_CREATED"
    REQUIREMENT_UPDATED = "REQUIREMENT_UPDATED"
    DECISION_CREATED = "DECISION_CREATED"
    DECISION_ACCEPTED = "DECISION_ACCEPTED"
    DECISION_REJECTED = "DECISION_REJECTED"
    DECISION_SUPERSEDED = "DECISION_SUPERSEDED"
    NOTE_CREATED = "NOTE_CREATED"
    REFERENCE_CREATED = "REFERENCE_CREATED"


@dataclass
class Event:
    event_type: EventType
    source_entity: str
    actor_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)