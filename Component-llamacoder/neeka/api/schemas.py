from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from neeka.brain.project import ProjectStatus
from neeka.brain.task import TaskPriority, TaskStatus
from neeka.brain.user import UserRole
from neeka.intelligence.permissions import PermissionMode


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    role: UserRole = UserRole.MEMBER


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, min_length=3, max_length=320)
    role: UserRole | None = None
    active: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: str
    role: UserRole
    active: bool
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    owner_id: str


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str
    owner_id: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    member_ids: list[str]
    task_ids: list[str]


class MemberRequest(BaseModel):
    user_id: str
    actor_id: str


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    creator_id: str
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    priority: TaskPriority | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    title: str
    description: str
    creator_id: str
    assigned_to: str | None
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    dependency_ids: list[str]


class ActorRequest(BaseModel):
    actor_id: str


class AssignmentRequest(BaseModel):
    user_id: str
    actor_id: str


class DependencyRequest(BaseModel):
    depends_on_id: str
    actor_id: str


class EventOut(BaseModel):
    event_id: str
    event_type: str
    timestamp: datetime
    actor_id: str
    entity_id: str
    metadata: dict[str, Any]


class ExecutionOut(BaseModel):
    execution_id: str
    event_id: str
    rule_id: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    error: str | None
    attempts: int


class WorkflowOut(BaseModel):
    workflow_id: str
    name: str
    description: str
    version: int
    active: bool
    states: list[str]
    transitions: list[dict[str, str]]


class ErrorOut(BaseModel):
    error: str
    message: str


class IntelligenceAnalyzeRequest(BaseModel):
    project_id: str
    mode: PermissionMode = PermissionMode.READ_ONLY


class IntelligencePlanRequest(BaseModel):
    project_id: str
    goal: str = Field(min_length=1, max_length=2000)
    mode: PermissionMode = PermissionMode.READ_ONLY


class IntelligenceActionRequest(BaseModel):
    action: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    mode: PermissionMode = PermissionMode.ASSISTED
    approved: bool = False