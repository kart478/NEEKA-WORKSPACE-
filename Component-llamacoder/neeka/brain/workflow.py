from .task import TaskStatus


class Workflow:
    VALID_TRANSITIONS = {
        TaskStatus.TODO: {TaskStatus.READY, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
        TaskStatus.READY: {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
        TaskStatus.IN_PROGRESS: {TaskStatus.BLOCKED, TaskStatus.COMPLETED, TaskStatus.CANCELLED},
        TaskStatus.BLOCKED: {TaskStatus.IN_PROGRESS, TaskStatus.READY, TaskStatus.CANCELLED},
        TaskStatus.COMPLETED: set(),
        TaskStatus.CANCELLED: set(),
    }

    @classmethod
    def can_transition(cls, current: TaskStatus, new_status: TaskStatus) -> bool:
        return new_status in cls.VALID_TRANSITIONS.get(current, set())