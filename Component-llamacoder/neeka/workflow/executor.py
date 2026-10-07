from datetime import datetime

from neeka.brain.task import Task, TaskStatus
from .definitions import STANDARD_TASK_WORKFLOW, WorkflowDefinition


class WorkflowExecutor:
    """Applies a validated workflow transition to a domain task."""

    def __init__(self, definition: WorkflowDefinition = STANDARD_TASK_WORKFLOW) -> None:
        self.definition = definition

    def transition(self, task: Task, destination: TaskStatus) -> str:
        transition = self.definition.state_machine.validate(task.status, destination)
        task.status = destination
        task.updated_at = datetime.utcnow()
        return transition.trigger