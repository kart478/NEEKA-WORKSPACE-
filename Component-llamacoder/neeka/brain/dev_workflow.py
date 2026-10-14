"""Developer workflow definitions, enums, and metadata dataclass.

This module introduces developer-specific workflow concepts without
replacing the existing TaskStatus state machine.  Developer stage
labels are stored in DevMetadata and validated here; the underlying
Task.status continues to use the existing TaskStatus values.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from neeka.brain.task import TaskStatus
from neeka.workflow.definitions import WorkflowDefinition
from neeka.workflow.state_machine import StateMachine, Transition


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class WorkflowType(str, Enum):
    FEATURE = "feature"
    BUG = "bug"
    CODE_REVIEW = "code_review"
    RELEASE = "release"


class DevWorkType(str, Enum):
    FEATURE = "feature"
    BUG = "bug"
    REFACTOR = "refactor"
    TECHNICAL_DEBT = "technical_debt"
    TEST = "test"
    DOCUMENTATION = "documentation"
    RELEASE = "release"


class DevSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


# ---------------------------------------------------------------------------
# Stage definitions
# Each WorkflowType has its own ordered stage list.
# Stages map to underlying TaskStatus values so the state machine stays clean.
# ---------------------------------------------------------------------------

FEATURE_STAGES: list[str] = [
    "Backlog",
    "Ready",
    "In Progress",
    "In Review",
    "Testing",
    "Done",
]

BUG_STAGES: list[str] = [
    "Reported",
    "Triaged",
    "Ready",
    "In Progress",
    "Fix Review",
    "Verification",
    "Resolved",
]

CODE_REVIEW_STAGES: list[str] = [
    "Requested",
    "In Review",
    "Changes Requested",
    "Approved",
    "Completed",
]

RELEASE_STAGES: list[str] = [
    "Planned",
    "In Preparation",
    "Validation",
    "Approval",
    "Released",
]

STAGES_BY_WORKFLOW: dict[WorkflowType, list[str]] = {
    WorkflowType.FEATURE: FEATURE_STAGES,
    WorkflowType.BUG: BUG_STAGES,
    WorkflowType.CODE_REVIEW: CODE_REVIEW_STAGES,
    WorkflowType.RELEASE: RELEASE_STAGES,
}

# Stage → underlying TaskStatus mapping
_STAGE_TO_STATUS: dict[str, TaskStatus] = {
    # Feature
    "Backlog": TaskStatus.TODO,
    "Ready": TaskStatus.READY,
    "In Progress": TaskStatus.IN_PROGRESS,
    "In Review": TaskStatus.IN_PROGRESS,
    "Testing": TaskStatus.IN_PROGRESS,
    "Done": TaskStatus.COMPLETED,
    # Bug
    "Reported": TaskStatus.TODO,
    "Triaged": TaskStatus.READY,
    # "Ready": already covered
    # "In Progress": already covered
    "Fix Review": TaskStatus.IN_PROGRESS,
    "Verification": TaskStatus.IN_PROGRESS,
    "Resolved": TaskStatus.COMPLETED,
    # Code Review
    "Requested": TaskStatus.TODO,
    # "In Review": already covered
    "Changes Requested": TaskStatus.BLOCKED,
    "Approved": TaskStatus.IN_PROGRESS,
    "Completed": TaskStatus.COMPLETED,
    # Release
    "Planned": TaskStatus.TODO,
    "In Preparation": TaskStatus.IN_PROGRESS,
    "Validation": TaskStatus.IN_PROGRESS,
    "Approval": TaskStatus.IN_PROGRESS,
    "Released": TaskStatus.COMPLETED,
}

# Stages that require explicit gate checks before completion
REQUIRES_VERIFICATION: frozenset[str] = frozenset({"Verification", "Resolved"})
REQUIRES_REVIEW_OUTCOME: frozenset[str] = frozenset({"Completed"})
RELEASE_TERMINAL_STAGES: frozenset[str] = frozenset({"Released"})


def stage_to_status(stage: str) -> TaskStatus:
    """Return the underlying TaskStatus for a dev stage label."""
    return _STAGE_TO_STATUS.get(stage, TaskStatus.IN_PROGRESS)


def valid_stages(workflow_type: WorkflowType) -> list[str]:
    return STAGES_BY_WORKFLOW[workflow_type]


def is_valid_stage(workflow_type: WorkflowType, stage: str) -> bool:
    return stage in STAGES_BY_WORKFLOW[workflow_type]


def next_stage(workflow_type: WorkflowType, current_stage: str) -> str | None:
    stages = STAGES_BY_WORKFLOW[workflow_type]
    try:
        idx = stages.index(current_stage)
        return stages[idx + 1] if idx + 1 < len(stages) else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Developer task metadata dataclass
# ---------------------------------------------------------------------------

@dataclass
class DevMetadata:
    """Optional per-task developer metadata stored in task_dev_metadata."""
    task_id: str
    work_type: DevWorkType = DevWorkType.FEATURE
    severity: DevSeverity | None = None
    stage: str = "Backlog"
    workflow_type: WorkflowType = WorkflowType.FEATURE
    acceptance_criteria: str = ""
    reproduction_steps: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""
    affected_component: str = ""
    repo_reference: str = ""
    external_issue: str = ""
    pull_request_reference: str = ""
    test_requirements: str = ""
    verification_result: str = ""
    target_milestone: str = ""
    review_outcome: str = ""
    blocking_task_ids: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def requires_verification_before_completion(self) -> bool:
        """True when the bug has explicit test requirements recorded."""
        return bool(self.test_requirements.strip())

    def verification_satisfied(self) -> bool:
        """True when verification_result has been recorded."""
        return bool(self.verification_result.strip())

    def requires_review_outcome(self) -> bool:
        """True for code-review tasks."""
        return self.workflow_type == WorkflowType.CODE_REVIEW

    def review_outcome_recorded(self) -> bool:
        return bool(self.review_outcome.strip())


# ---------------------------------------------------------------------------
# Workflow definitions (reuse existing StateMachine + WorkflowDefinition)
# ---------------------------------------------------------------------------

def _make_standard_transitions() -> frozenset[Transition]:
    """Shared base transitions for all developer workflows."""
    return frozenset({
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
    })


FEATURE_WORKFLOW = WorkflowDefinition(
    workflow_id="dev_feature",
    name="Feature Development",
    description="Backlog → Ready → In Progress → In Review → Testing → Done",
    version=1,
    active=True,
    state_machine=StateMachine(
        states=frozenset(TaskStatus),
        transitions=_make_standard_transitions(),
    ),
)

BUG_WORKFLOW = WorkflowDefinition(
    workflow_id="dev_bug",
    name="Bug Resolution",
    description="Reported → Triaged → Ready → In Progress → Fix Review → Verification → Resolved",
    version=1,
    active=True,
    state_machine=StateMachine(
        states=frozenset(TaskStatus),
        transitions=_make_standard_transitions(),
    ),
)

CODE_REVIEW_WORKFLOW = WorkflowDefinition(
    workflow_id="dev_code_review",
    name="Code Review",
    description="Requested → In Review → Changes Requested or Approved → Completed",
    version=1,
    active=True,
    state_machine=StateMachine(
        states=frozenset(TaskStatus),
        transitions=_make_standard_transitions() | frozenset({
            Transition(TaskStatus.IN_PROGRESS, TaskStatus.READY, "review_changes_requested"),
        }),
    ),
)

RELEASE_WORKFLOW = WorkflowDefinition(
    workflow_id="dev_release",
    name="Software Release",
    description="Planned → In Preparation → Validation → Approval → Released",
    version=1,
    active=True,
    state_machine=StateMachine(
        states=frozenset(TaskStatus),
        transitions=_make_standard_transitions(),
    ),
)

DEV_WORKFLOWS: dict[WorkflowType, WorkflowDefinition] = {
    WorkflowType.FEATURE: FEATURE_WORKFLOW,
    WorkflowType.BUG: BUG_WORKFLOW,
    WorkflowType.CODE_REVIEW: CODE_REVIEW_WORKFLOW,
    WorkflowType.RELEASE: RELEASE_WORKFLOW,
}

ALL_DEV_WORKFLOWS: list[WorkflowDefinition] = list(DEV_WORKFLOWS.values())
