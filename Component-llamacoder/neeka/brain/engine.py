import logging
from datetime import datetime
from pathlib import Path

from neeka.persistence.database import Database
from neeka.persistence.repositories import EventRepository, ProjectRepository, TaskRepository, UserRepository
from neeka.persistence.sqlite_repositories import (
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