from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from neeka.brain.project import ProjectStatus
from neeka.brain.task import TaskPriority, TaskStatus
from neeka.brain.user import UserRole
from neeka.intelligence.permissions import PermissionMode
from neeka.knowledge.decision import DecisionStatus
from neeka.knowledge.document import DocumentStatus, DocumentType
from neeka.knowledge.requirement import RequirementPriority, RequirementStatus
from neeka.artifacts.artifact import ArtifactStatus, ArtifactType
from neeka.artifacts.relationships import ArtifactRole


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


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    content: str = ""
    document_type: DocumentType = DocumentType.OTHER
    status: DocumentStatus = DocumentStatus.DRAFT
    actor_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    content: str | None = None
    document_type: DocumentType | None = None
    status: DocumentStatus | None = None
    metadata: dict[str, Any] | None = None
    actor_id: str


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    title: str
    description: str
    content: str
    document_type: DocumentType
    status: DocumentStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    version: int
    metadata: dict[str, Any]


class RequirementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    priority: RequirementPriority = RequirementPriority.MEDIUM
    source: str = ""
    actor_id: str


class RequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    title: str
    description: str
    priority: RequirementPriority
    status: RequirementStatus
    source: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class DecisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    decision: str = Field(min_length=1)
    reason: str = ""
    alternatives_considered: list[str] = Field(default_factory=list)
    status: DecisionStatus = DecisionStatus.PROPOSED
    actor_id: str


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    title: str
    decision: str
    reason: str
    alternatives_considered: list[str]
    status: DecisionStatus
    superseded_by: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = ""
    tags: list[str] = Field(default_factory=list)
    actor_id: str


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    title: str
    content: str
    author: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class ReferenceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    url: str
    description: str = ""
    source_type: str = "OTHER"
    actor_id: str


class ReferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    title: str
    url: str
    description: str
    source_type: str
    created_by: str
    created_at: datetime


class ArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    name: str
    description: str
    artifact_type: ArtifactType
    mime_type: str
    size: int
    checksum: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    status: ArtifactStatus
    metadata: dict[str, Any]
    current_version: int


class ArtifactVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    artifact_id: str
    version_number: int
    size: int
    checksum: str
    created_by: str
    created_at: datetime


class ArtifactAttachRequest(BaseModel):
    target_type: str = Field(min_length=1, max_length=50)
    target_id: str
    role: ArtifactRole = ArtifactRole.ATTACHMENT
    actor_id: str