import logging
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from neeka.persistence.database import Database
from neeka.persistence.repositories import EventRepository, ProjectRepository, TaskRepository, UserRepository
from neeka.knowledge.decision import Decision
from neeka.knowledge.document import Document
from neeka.knowledge.note import Note
from neeka.knowledge.reference import Reference
from neeka.knowledge.repositories.base import KnowledgeRepository
from neeka.knowledge.repositories.sqlite import SQLiteKnowledgeRepository
from neeka.knowledge.requirement import Requirement
from neeka.knowledge.services import KnowledgeService
from neeka.artifacts.artifact import Artifact, ArtifactType
from neeka.artifacts.repositories.base import ArtifactRepository
from neeka.artifacts.repositories.sqlite import SQLiteArtifactRepository
from neeka.artifacts.relationships import ArtifactRelationship, ArtifactRole
from neeka.artifacts.services import ArtifactService
from neeka.artifacts.storage import LocalArtifactStorage
from neeka.persistence.sqlite_repositories import (
    SQLiteAIAuditRepository,
    SQLiteAutomationExecutionRepository,
    SQLiteEventRepository,
    SQLiteProjectRepository,
    SQLiteTaskRepository,
    SQLiteUserRepository,
)
from neeka.automation.engine import AutomationEngine
from .event import Event, EventType
from .exceptions import (
    CircularDependencyError,
    AutomationExecutionNotFoundError,
    DuplicateMemberError,
    InactiveUserError,
    EventNotFoundError,
    InvalidProjectMembershipError,
    InvalidTaskTransitionError,
    ProjectNotFoundError,
    TaskDependencyError,
    TaskNotFoundError,
    UserNotFoundError,
)
from .project import Project, ProjectStatus
from .task import Task, TaskPriority, TaskStatus
from .user import User, UserRole
from .workflow import Workflow
from neeka.workflow.executor import WorkflowExecutor

logger = logging.getLogger(__name__)


class NEEKAEngine:
    """Application coordinator; domain behavior is persisted through repositories."""

    def __init__(
        self,
        db_path: str | Path = "data/neeka.db",
        user_repository: UserRepository | None = None,
        project_repository: ProjectRepository | None = None,
        task_repository: TaskRepository | None = None,
        event_repository: EventRepository | None = None,
        automation_execution_repository=None,
        knowledge_repository: KnowledgeRepository | None = None,
        artifact_repository: ArtifactRepository | None = None,
        artifact_storage=None,
        artifact_max_size: int = 50 * 1024 * 1024,
    ) -> None:
        self.database = Database(db_path)
        self._users: dict[str, User] = {}
        self._projects: dict[str, Project] = {}
        self._tasks: dict[str, Task] = {}
        self._events: list[Event] = []
        self.users = user_repository or SQLiteUserRepository(self.database)
        self.projects = project_repository or SQLiteProjectRepository(self.database)
        self.tasks = task_repository or SQLiteTaskRepository(self.database)
        self.events = event_repository or SQLiteEventRepository(self.database)
        self.automation_executions = automation_execution_repository or SQLiteAutomationExecutionRepository(self.database)
        self.ai_audit_repository = SQLiteAIAuditRepository(self.database)
        self.knowledge_repository = knowledge_repository or SQLiteKnowledgeRepository(self.database)
        self.knowledge = KnowledgeService(self.knowledge_repository, self._can_access_knowledge)
        self.artifact_repository = artifact_repository or SQLiteArtifactRepository(self.database)
        storage_root = Path("data/artifacts") if str(db_path) == ":memory:" else Path(db_path).parent / "artifacts"
        self.artifact_storage = artifact_storage or LocalArtifactStorage(storage_root)
        self.artifacts = ArtifactService(self.artifact_repository, self.artifact_storage,
                         self._can_access_knowledge, artifact_max_size)
        self.workflow = WorkflowExecutor()
        self.automation = AutomationEngine(self, self.automation_executions)
        self._load()
        logger.info("NEEKA started with database %s", db_path)

    def _load(self) -> None:
        self._users = {user.id: user for user in self.users.list()}
        self._projects = {project.id: project for project in self.projects.list()}
        self._tasks = {task.id: task for task in self.tasks.list()}
        self._events = self.events.list()

    def close(self) -> None:
        logger.info("NEEKA shutting down")
        self.database.close()

    def _can_access_knowledge(self, project_id: str, actor_id: str) -> bool:
        project = self._projects.get(project_id)
        return project is not None and actor_id in project.member_ids

    def create_document(self, document: Document, actor_id: str) -> Document:
        result = self.knowledge.create_document(document, actor_id)
        self._emit_event(EventType.DOCUMENT_CREATED, result.id, actor_id, {"project_id": result.project_id})
        self._emit_event(EventType.DOCUMENT_VERSION_CREATED, result.id, actor_id, {"project_id": result.project_id, "version": result.version})
        return result

    def update_document(self, document_id: str, actor_id: str, **changes) -> Document:
        result = self.knowledge.update_document(document_id, actor_id, **changes)
        self._emit_event(EventType.DOCUMENT_UPDATED, result.id, actor_id, {"project_id": result.project_id})
        self._emit_event(EventType.DOCUMENT_VERSION_CREATED, result.id, actor_id, {"project_id": result.project_id, "version": result.version})
        return result

    def get_document(self, document_id: str, actor_id: str) -> Document:
        document = self.knowledge_repository.get_document(document_id)
        if document is None:
            raise KeyError(document_id)
        self.knowledge._check(document.project_id, actor_id)
        return document

    def list_documents(self, project_id: str, actor_id: str) -> list[Document]:
        self.knowledge._check(project_id, actor_id)
        return self.knowledge_repository.list_documents(project_id)

    def document_versions(self, document_id: str, actor_id: str):
        document = self.get_document(document_id, actor_id)
        return self.knowledge_repository.list_document_versions(document.id)

    def create_requirement(self, item: Requirement, actor_id: str) -> Requirement:
        result = self.knowledge.create_requirement(item, actor_id)
        self._emit_event(EventType.REQUIREMENT_CREATED, result.id, actor_id, {"project_id": result.project_id})
        return result

    def list_requirements(self, project_id: str, actor_id: str) -> list[Requirement]:
        self.knowledge._check(project_id, actor_id)
        return self.knowledge_repository.list_requirements(project_id)

    def create_decision(self, item: Decision, actor_id: str) -> Decision:
        result = self.knowledge.create_decision(item, actor_id)
        self._emit_event(EventType.DECISION_CREATED, result.id, actor_id, {"project_id": result.project_id})
        return result

    def list_decisions(self, project_id: str, actor_id: str) -> list[Decision]:
        self.knowledge._check(project_id, actor_id)
        return self.knowledge_repository.list_decisions(project_id)

    def update_decision(self, decision_id: str, project_id: str, actor_id: str, **changes) -> Decision:
        result = self.knowledge.update_decision(decision_id, actor_id, project_id=project_id, **changes)
        event_type = EventType.DECISION_SUPERSEDED if result.status.value == "SUPERSEDED" else EventType.DECISION_ACCEPTED if result.status.value == "ACCEPTED" else EventType.DECISION_REJECTED if result.status.value == "REJECTED" else EventType.DECISION_CREATED
        self._emit_event(event_type, result.id, actor_id, {"project_id": result.project_id})
        return result

    def add_knowledge_relationship(self, project_id: str, actor_id: str, source_type: str, source_id: str,
                                    relationship: str, target_type: str, target_id: str) -> None:
        self.knowledge.add_relationship(project_id, actor_id, source_type, source_id, relationship, target_type, target_id)

    def create_note(self, item: Note, actor_id: str) -> Note:
        result = self.knowledge.create_note(item, actor_id)
        self._emit_event(EventType.NOTE_CREATED, result.id, actor_id, {"project_id": result.project_id})
        return result

    def list_notes(self, project_id: str, actor_id: str) -> list[Note]:
        self.knowledge._check(project_id, actor_id)
        return self.knowledge_repository.list_notes(project_id)

    def create_reference(self, item: Reference, actor_id: str) -> Reference:
        result = self.knowledge.create_reference(item, actor_id)
        self._emit_event(EventType.REFERENCE_CREATED, result.id, actor_id, {"project_id": result.project_id})
        return result

    def list_references(self, project_id: str, actor_id: str) -> list[Reference]:
        self.knowledge._check(project_id, actor_id)
        return self.knowledge_repository.list_references(project_id)

    def get_project_knowledge(self, project_id: str, actor_id: str):
        return self.knowledge.project(project_id, actor_id)

    def search_knowledge(self, project_id: str, actor_id: str, keyword: str, type: str | None = None, status: str | None = None) -> list[dict]:
        self.knowledge._check(project_id, actor_id)
        return self.knowledge_repository.search(project_id, keyword, type, status)

    def create_artifact(self, project_id: str, name: str, description: str, artifact_type: ArtifactType,
                        mime_type: str, source: BinaryIO, actor_id: str, metadata: dict | None = None) -> Artifact:
        artifact = self.artifacts.create(project_id, name, description, artifact_type, mime_type, source, actor_id, metadata)
        self._emit_event(EventType.ARTIFACT_CREATED, artifact.id, actor_id, {"project_id": project_id, "version": 1})
        self._emit_event(EventType.ARTIFACT_UPLOADED, artifact.id, actor_id, {"project_id": project_id, "size": artifact.size})
        return artifact

    def get_artifact(self, artifact_id: str, actor_id: str) -> Artifact:
        return self.artifacts.get(artifact_id, actor_id)

    def list_artifacts(self, project_id: str, actor_id: str) -> list[Artifact]:
        return self.artifacts.list(project_id, actor_id)

    def artifact_versions(self, artifact_id: str, actor_id: str):
        return self.artifacts.versions(artifact_id, actor_id)

    def restore_artifact_version(self, artifact_id: str, version_number: int, actor_id: str) -> Artifact:
        artifact = self.artifacts.restore_version(artifact_id, version_number, actor_id)
        self._emit_event(EventType.ARTIFACT_RESTORED, artifact.id, actor_id,
                         {"project_id": artifact.project_id, "version": version_number})
        return artifact

    def create_artifact_version(self, artifact_id: str, source: BinaryIO, actor_id: str,
                                metadata: dict | None = None) -> Artifact:
        artifact = self.artifacts.add_version(artifact_id, source, actor_id, metadata)
        self._emit_event(EventType.ARTIFACT_VERSION_CREATED, artifact.id, actor_id,
                         {"project_id": artifact.project_id, "version": artifact.current_version})
        return artifact

    def read_artifact(self, artifact_id: str, actor_id: str):
        return self.artifacts.read(artifact_id, actor_id)

    def delete_artifact(self, artifact_id: str, actor_id: str) -> Artifact:
        artifact = self.artifacts.remove(artifact_id, actor_id)
        self._emit_event(EventType.ARTIFACT_DELETED, artifact.id, actor_id, {"project_id": artifact.project_id})
        return artifact

    def attach_artifact(self, artifact_id: str, target_type: str, target_id: str,
                        role: ArtifactRole, actor_id: str) -> ArtifactRelationship:
        relationship = self.artifacts.attach(artifact_id, target_type, target_id, role, actor_id)
        artifact = self.get_artifact(artifact_id, actor_id)
        self._emit_event(EventType.ARTIFACT_ATTACHED, artifact_id, actor_id,
                         {"project_id": artifact.project_id, "target_type": target_type, "target_id": target_id, "role": role.value})
        return relationship

    def artifact_relationships(self, artifact_id: str, actor_id: str) -> list[ArtifactRelationship]:
        return self.artifacts.relationships(artifact_id, actor_id)

    def detach_artifact(self, artifact_id: str, target_type: str, target_id: str,
                        role: ArtifactRole, actor_id: str) -> None:
        artifact = self.get_artifact(artifact_id, actor_id)
        self.artifacts.detach(artifact_id, target_type, target_id, role, actor_id)
        self._emit_event(EventType.ARTIFACT_DETACHED, artifact_id, actor_id,
                         {"project_id": artifact.project_id, "target_type": target_type, "target_id": target_id, "role": role.value})

    def task_artifacts(self, task_id: str, actor_id: str) -> list[Artifact]:
        task = self.get_task(task_id)
        self.artifacts.permissions.check(task.project_id, actor_id)
        return self.artifact_repository.artifacts_for_target("task", task_id)

    @staticmethod
    def utcnow() -> datetime:
        return datetime.utcnow()

    def create_user(self, name: str, email: str, role: UserRole = UserRole.MEMBER) -> User:
        user = User(name=name, email=email, role=role)
        self.users.save(user)
        self._users[user.id] = user
        logger.info("User created: %s", user.id)
        return user

    def get_user(self, user_id: str) -> User:
        if user_id not in self._users:
            raise UserNotFoundError(f"User {user_id} not found")
        return self._users[user_id]

    def list_users(self) -> list[User]:
        return list(self._users.values())

    def list_users(self) -> list[User]:
        return list(self._users.values())

    def update_user(self, user: User) -> None:
        self.get_user(user.id)
        user.updated_at = datetime.utcnow()
        self.users.save(user)

    def create_project(self, name: str, description: str, owner_id: str) -> Project:
        self.get_user(owner_id)
        project = Project(name=name, description=description, owner_id=owner_id)
        project.add_member(owner_id)
        self.projects.save(project)
        self._projects[project.id] = project
        self._emit_event(EventType.PROJECT_CREATED, project.id, owner_id, {"project_name": name})
        logger.info("Project created: %s", project.id)
        return project

    def get_project(self, project_id: str) -> Project:
        if project_id not in self._projects:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        return self._projects[project_id]

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def update_project(self, project_id: str, name: str | None = None, description: str | None = None) -> Project:
        project = self.get_project(project_id)
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        project.updated_at = datetime.utcnow()
        self.projects.save(project)
        return project

    def delete_project(self, project_id: str, actor_id: str) -> None:
        project = self.get_project(project_id)
        if project.owner_id != actor_id:
            raise InvalidProjectMembershipError("Only the project owner can delete a project")
        self.get_user(actor_id)
        self.projects.delete(project_id)
        self._projects.pop(project_id, None)
        for task_id in project.task_ids:
            self._tasks.pop(task_id, None)

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def update_project(self, project_id: str, name: str | None = None, description: str | None = None) -> Project:
        project = self.get_project(project_id)
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        project.updated_at = datetime.utcnow()
        self.projects.save(project)
        return project

    def delete_project(self, project_id: str, actor_id: str) -> None:
        project = self.get_project(project_id)
        if project.owner_id != actor_id:
            raise InvalidProjectMembershipError("Only the project owner can delete a project")
        self.get_user(actor_id)
        self.projects.delete(project_id)
        self._projects.pop(project_id, None)
        for task_id in project.task_ids:
            self._tasks.pop(task_id, None)

    def remove_project_member(self, project_id: str, user_id: str, actor_id: str) -> None:
        project = self.get_project(project_id)
        self.get_user(actor_id)
        if project.owner_id == user_id:
            raise InvalidProjectMembershipError("The project owner cannot be removed")
        if not self.projects.has_member(project_id, actor_id):
            raise InvalidProjectMembershipError(f"Actor {actor_id} is not a project member")
        if user_id not in project.member_ids:
            raise InvalidProjectMembershipError(f"User {user_id} is not a project member")
        self.projects.remove_member(project_id, user_id)
        project.member_ids.remove(user_id)
        self._emit_event(EventType.USER_REMOVED_FROM_PROJECT, project_id, actor_id, {"user_id": user_id})

    def add_project_member(self, project_id: str, user_id: str, actor_id: str) -> None:
        project = self.get_project(project_id)
        self.get_user(user_id)
        self.get_user(actor_id)
        if not self.projects.has_member(project_id, actor_id):
            raise InvalidProjectMembershipError(f"Actor {actor_id} is not a project member")
        if user_id in project.member_ids:
            raise DuplicateMemberError(f"User {user_id} is already a member of project {project_id}")
        self.projects.add_member(project_id, user_id, "MEMBER")
        project.add_member(user_id)
        self._emit_event(EventType.USER_ADDED_TO_PROJECT, project_id, actor_id, {"user_id": user_id})

    def remove_project_member(self, project_id: str, user_id: str, actor_id: str) -> None:
        project = self.get_project(project_id)
        self.get_user(actor_id)
        if project.owner_id == user_id:
            raise InvalidProjectMembershipError("The project owner cannot be removed")
        if not self.projects.has_member(project_id, actor_id):
            raise InvalidProjectMembershipError(f"Actor {actor_id} is not a project member")
        if user_id not in project.member_ids:
            raise InvalidProjectMembershipError(f"User {user_id} is not a project member")
        self.projects.remove_member(project_id, user_id)
        project.member_ids.remove(user_id)
        self._emit_event(EventType.USER_REMOVED_FROM_PROJECT, project_id, actor_id, {"user_id": user_id})

    def create_task(
        self,
        title: str,
        description: str,
        project_id: str,
        creator_id: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> Task:
        project = self.get_project(project_id)
        self.get_user(creator_id)
        if not self.projects.has_member(project_id, creator_id):
            raise InvalidProjectMembershipError(f"Creator {creator_id} is not a project member")
        task = Task(title=title, description=description, project_id=project_id,
                    creator_id=creator_id, priority=priority)
        self.tasks.save(task)
        self._tasks[task.id] = task
        project.add_task(task.id)
        self.projects.save(project)
        self._emit_event(EventType.TASK_CREATED, task.id, creator_id, {"project_id": project_id})
        logger.info("Task created: %s", task.id)
        return task

    def get_task(self, task_id: str) -> Task:
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task {task_id} not found")
        return self._tasks[task_id]

    def list_tasks(self, project_id: str | None = None) -> list[Task]:
        return [task for task in self._tasks.values()
                if project_id is None or task.project_id == project_id]

    def update_task(self, task_id: str, title: str | None = None, description: str | None = None,
                    priority: TaskPriority | None = None) -> Task:
        task = self.get_task(task_id)
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        task.updated_at = datetime.utcnow()
        self.tasks.save(task)
        return task

    def list_tasks(self, project_id: str | None = None) -> list[Task]:
        tasks = list(self._tasks.values())
        return [task for task in tasks if project_id is None or task.project_id == project_id]

    def update_task(self, task_id: str, title: str | None = None, description: str | None = None,
                    priority: TaskPriority | None = None) -> Task:
        task = self.get_task(task_id)
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        task.updated_at = datetime.utcnow()
        self.tasks.save(task)
        return task

    def assign_task(self, task_id: str, user_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        user = self.get_user(user_id)
        self.get_user(actor_id)
        if not self.projects.has_member(task.project_id, user_id):
            raise InvalidProjectMembershipError(f"User {user_id} is not a project member")
        if not user.active:
            raise InactiveUserError(f"Cannot assign task to inactive user {user_id}")
        if task.status == TaskStatus.COMPLETED:
            raise InvalidTaskTransitionError("Cannot assign a completed task")
        if task.assigned_to == user_id:
            return
        task.assigned_to = user_id
        task.updated_at = datetime.utcnow()
        self.tasks.save(task)
        self._emit_event(EventType.TASK_ASSIGNED, task_id, actor_id, {"user_id": user_id})
        logger.info("Task assigned: %s", task_id)

    def add_task_dependency(self, task_id: str, depends_on_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        dependency = self.get_task(depends_on_id)
        self.get_user(actor_id)
        if task.project_id != dependency.project_id:
            raise TaskDependencyError("Tasks in different projects cannot be linked")
        if task_id == depends_on_id or self._would_cycle(task_id, depends_on_id):
            raise CircularDependencyError("Adding this dependency would create a cycle")
        if depends_on_id in task.dependency_ids:
            raise TaskDependencyError("Dependency already exists")
        self.tasks.add_dependency(task_id, depends_on_id)
        task.add_dependency(depends_on_id)
        if not task.dependencies_satisfied(self._tasks):
            self.workflow.transition(task, TaskStatus.BLOCKED)
            self.tasks.save(task)
            self._emit_event(EventType.TASK_BLOCKED, task_id, actor_id, {"reason": "dependency_added"})

    def remove_task_dependency(self, task_id: str, depends_on_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        self.get_task(depends_on_id)
        self.get_user(actor_id)
        if depends_on_id not in task.dependency_ids:
            return
        self.tasks.remove_dependency(task_id, depends_on_id)
        task.dependency_ids.remove(depends_on_id)
        if task.status == TaskStatus.BLOCKED and task.dependencies_satisfied(self._tasks):
            self.workflow.transition(task, TaskStatus.READY)
        self.tasks.save(task)

    def block_task(self, task_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        self.get_user(actor_id)
        self._transition_task(task, TaskStatus.BLOCKED)
        self.tasks.save(task)
        self._emit_event(EventType.TASK_BLOCKED, task_id, actor_id, {"reason": "manual"})

    def _would_cycle(self, task_id: str, depends_on_id: str) -> bool:
        seen: set[str] = set()

        def visit(current: str) -> bool:
            if current == task_id:
                return True
            if current in seen:
                return False
            seen.add(current)
            return any(visit(parent) for parent in self.get_task(current).dependency_ids)

        return visit(depends_on_id)

    def start_task(self, task_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        self.get_user(actor_id)
        if not task.dependencies_satisfied(self._tasks):
            raise TaskDependencyError(f"Task {task_id} has unsatisfied dependencies")
        if task.status == TaskStatus.TODO:
            self.workflow.transition(task, TaskStatus.READY)
        self._transition_task(task, TaskStatus.IN_PROGRESS)
        task.started_at = datetime.utcnow()
        self.tasks.save(task)
        self._emit_event(EventType.TASK_STARTED, task_id, actor_id)
        logger.info("Task started: %s", task_id)

    def complete_task(self, task_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        self.get_user(actor_id)
        if task.status == TaskStatus.COMPLETED:
            return
        self._transition_task(task, TaskStatus.COMPLETED)
        task.completed_at = datetime.utcnow()
        self.tasks.save(task)
        self._emit_event(EventType.TASK_COMPLETED, task_id, actor_id)
        self._check_project_completion(task.project_id)
        logger.info("Task completed: %s", task_id)

    def cancel_task(self, task_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        self.get_user(actor_id)
        self._transition_task(task, TaskStatus.CANCELLED)
        self.tasks.save(task)
        self._emit_event(EventType.TASK_CANCELLED, task_id, actor_id)

    def _transition_task(self, task: Task, new_status: TaskStatus) -> None:
        self.workflow.transition(task, new_status)

    def transition_task(self, task_id: str, new_status: TaskStatus, actor_id: str) -> Task:
        task = self.get_task(task_id)
        self.get_user(actor_id)
        self._transition_task(task, new_status)
        self.tasks.save(task)
        return task

    def _unlock_dependent_tasks(self, completed_task_id: str, actor_id: str, metadata: dict | None = None) -> None:
        depth = int((metadata or {}).get("_automation_depth", 0)) + 1
        for task in self._tasks.values():
            if completed_task_id in task.dependency_ids and task.dependencies_satisfied(self._tasks):
                if task.status in (TaskStatus.BLOCKED, TaskStatus.TODO):
                    self.workflow.transition(task, TaskStatus.READY)
                    self.tasks.save(task)
                    self._emit_event(
                        EventType.TASK_READY,
                        task.id,
                        actor_id,
                        {"reason": "dependencies_satisfied", "_automation_depth": depth},
                    )

    def _check_dependent_tasks(self, completed_task_id: str, actor_id: str) -> None:
        """Compatibility alias for callers from the Part 2 engine."""
        self._unlock_dependent_tasks(completed_task_id, actor_id)

    def _check_project_completion(self, project_id: str) -> None:
        project = self.get_project(project_id)
        if project.task_ids and all(self._tasks[task_id].status == TaskStatus.COMPLETED for task_id in project.task_ids):
            project.status = ProjectStatus.COMPLETED
            project.updated_at = datetime.utcnow()
            self.projects.save(project)

    def _emit_event(self, event_type: EventType, source_entity: str, actor_id: str, metadata: dict | None = None) -> None:
        event = Event(event_type=event_type, source_entity=source_entity, actor_id=actor_id, metadata=metadata or {})
        self.events.append(event)
        self._events.append(event)
        self.automation.process_event(event)

    def get_events(self) -> list[Event]:
        return self._events.copy()

    def get_event(self, event_id: str) -> Event:
        for event in self._events:
            if event.id == event_id:
                return event
        raise EventNotFoundError(f"Event {event_id} not found")

    def list_automation_executions(self) -> list[dict]:
        return self.automation_executions.list()

    def retry_automation(self, execution_id: str) -> dict:
        record = next((item for item in self.automation_executions.list()
                       if item["execution_id"] == execution_id), None)
        if record is None:
            raise AutomationExecutionNotFoundError(f"Automation execution {execution_id} not found")
        event = self.get_event(record["event_id"])
        self.automation.process_event(event, retry_failed=True)
        return next(item for item in self.automation_executions.list()
                    if item["execution_id"] == execution_id)

    def get_project_tasks(self, project_id: str) -> list[Task]:
        project = self.get_project(project_id)
        return [self._tasks[task_id] for task_id in project.task_ids]