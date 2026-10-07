from dataclasses import dataclass

from neeka.brain.task import TaskStatus
from .state_machine import StateMachine, Transition


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    name: str
    description: str
    version: int
    active: bool
    state_machine: StateMachine


STANDARD_TASK_WORKFLOW = WorkflowDefinition(
    workflow_id="standard_project_task",
    name="Standard Project Task",
    description="The default lifecycle for project tasks.",
    version=1,
    active=True,
    state_machine=StateMachine(
        states=frozenset(TaskStatus),
        transitions=frozenset({
            Transition(TaskStatus.TODO, TaskStatus.READY, "task_ready"),
            Transition(TaskStatus.READY, TaskStatus.IN_PROGRESS, "task_started"),
            Transition(TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED, "task_completed"),
            Transition(TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, "task_blocked"),
            Transition(TaskStatus.BLOCKED, TaskStatus.IN_PROGRESS, "task_unblocked"),
            Transition(TaskStatus.BLOCKED, TaskStatus.READY, "task_ready"),
            Transition(TaskStatus.TODO, TaskStatus.BLOCKED, "dependency_added"),
            Transition(TaskStatus.TODO, TaskStatus.CANCELLED, "task_cancelled"),
            Transition(TaskStatus.READY, TaskStatus.CANCELLED, "task_cancelled"),
            Transition(TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED, "task_cancelled"),
            Transition(TaskStatus.BLOCKED, TaskStatus.CANCELLED, "task_cancelled"),
        }),
    ),
)