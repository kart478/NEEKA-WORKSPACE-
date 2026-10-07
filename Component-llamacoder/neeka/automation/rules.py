from dataclasses import dataclass
from typing import Callable

from neeka.brain.event import Event, EventType
from .actions import AutomationAction, UnlockDependentTasksAction


@dataclass(frozen=True)
class AutomationRule:
    rule_id: str
    trigger: EventType
    condition: Callable[[object, Event], bool]
    action: AutomationAction


def dependency_completion_rule() -> AutomationRule:
    return AutomationRule(
        rule_id="unlock-completed-task-dependents",
        trigger=EventType.TASK_COMPLETED,
        condition=lambda engine, event: event.source_entity in engine._tasks,
        action=UnlockDependentTasksAction(),
    )