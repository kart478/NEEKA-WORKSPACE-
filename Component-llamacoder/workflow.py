# brain/workflow.py
from enum import Enum
from typing import Dict, Set
from .task import TaskStatus


class Workflow:
    """Validates task state transitions."""

    VALID_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
        TaskStatus.TODO: {TaskStatus.READY, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
        TaskStatus.READY: {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
        TaskStatus.IN_PROGRESS: {TaskStatus.BLOCKED, TaskStatus.COMPLETED, TaskStatus.CANCELLED},
        TaskStatus.BLOCKED: {TaskStatus.IN_PROGRESS, TaskStatus.READY, TaskStatus.CANCELLED},
        TaskStatus.COMPLETED: set(),
        TaskStatus.CANCELLED: set(),
    }

    @classmethod
    def can_transition(cls, current: TaskStatus, new: TaskStatus) -> bool:
        return new in cls.VALID_TRANSITIONS.get(current, set())