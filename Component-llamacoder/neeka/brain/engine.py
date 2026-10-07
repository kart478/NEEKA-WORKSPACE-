import logging
from datetime import datetime
from pathlib import Path

from neeka.persistence.database import Database
from neeka.persistence.repositories import EventRepository, ProjectRepository, TaskRepository, UserRepository
from neeka.persistence.sqlite_repositories import (
    SQLiteEventRepository,
    SQLiteProjectRepository,
    SQLiteTaskRepository,
    SQLiteUserRepository,
)
from .event import Event, EventType
from .exceptions import (
    CircularDependencyError,
    DuplicateMemberError,
    InactiveUserError,
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
        self._load()
        logger.info("NEEKA started with database %s", db_path)

    def _load(self) -> None:
        self._users = {user.id: user for user in self.users.list()}
        self._projects = {project.id: project for project in self.projects.list()}
        self._tasks = {task.id: task for task in self.tasks.list()}
        self._events = self.events.list()

    def close(self) -> None:
        logger.info("NEEKA shutting down")

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
            task.status = TaskStatus.BLOCKED
            self.tasks.save(task)
            self._emit_event(EventType.TASK_BLOCKED, task_id, actor_id, {"reason": "dependency_added"})

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
            task.status = TaskStatus.READY
        self._transition_task(task, TaskStatus.IN_PROGRESS)
        task.started_at = datetime.utcnow()
        self.tasks.save(task)
        self._emit_event(EventType.TASK_STARTED, task_id, actor_id)
        logger.info("Task started: %s", task_id)

    def complete_task(self, task_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        self.get_user(actor_id)
        self._transition_task(task, TaskStatus.COMPLETED)
        task.completed_at = datetime.utcnow()
        self.tasks.save(task)
        self._emit_event(EventType.TASK_COMPLETED, task_id, actor_id)
        self._check_dependent_tasks(task_id, actor_id)
        self._check_project_completion(task.project_id)
        logger.info("Task completed: %s", task_id)

    def cancel_task(self, task_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        self.get_user(actor_id)
        self._transition_task(task, TaskStatus.CANCELLED)
        self.tasks.save(task)
        self._emit_event(EventType.TASK_CANCELLED, task_id, actor_id)

    def _transition_task(self, task: Task, new_status: TaskStatus) -> None:
        if not Workflow.can_transition(task.status, new_status):
            raise InvalidTaskTransitionError(f"Cannot transition task {task.id} from {task.status} to {new_status}")
        task.status = new_status
        task.updated_at = datetime.utcnow()

    def _check_dependent_tasks(self, completed_task_id: str, actor_id: str) -> None:
        for task in self._tasks.values():
            if completed_task_id in task.dependency_ids and task.dependencies_satisfied(self._tasks):
                if task.status in (TaskStatus.BLOCKED, TaskStatus.TODO):
                    task.status = TaskStatus.READY
                    task.updated_at = datetime.utcnow()
                    self.tasks.save(task)
                    self._emit_event(EventType.TASK_READY, task.id, actor_id, {"reason": "dependencies_satisfied"})

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

    def get_events(self) -> list[Event]:
        return self._events.copy()

    def get_project_tasks(self, project_id: str) -> list[Task]:
        project = self.get_project(project_id)
        return [self._tasks[task_id] for task_id in project.task_ids]