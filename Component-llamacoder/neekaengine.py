# brain/engine.py
from typing import Dict, List, Optional
from .user import User, UserRole
from .project import Project, ProjectStatus
from .task import Task, TaskStatus, TaskPriority
from .workflow import Workflow
from .event import Event, EventType
from .exceptions import (
    ProjectNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
    InvalidTaskTransitionError,
    TaskDependencyError,
    InactiveUserError,
    DuplicateMemberError,
)


class NEEKAEngine:
    """Central coordinator for the NEEKA Brain."""

    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._projects: Dict[str, Project] = {}
        self._tasks: Dict[str, Task] = {}
        self._events: List[Event] = []

    # --- User Management ---

    def create_user(self, name: str, email: str, role: UserRole = UserRole.MEMBER) -> User:
        user = User(name=name, email=email, role=role)
        self._users[user.id] = user
        return user

    def get_user(self, user_id: str) -> User:
        if user_id not in self._users:
            raise UserNotFoundError(f"User {user_id} not found")
        return self._users[user_id]

    # --- Project Management ---

    def create_project(self, name: str, description: str, owner_id: str) -> Project:
        self.get_user(owner_id)  # Validate owner exists
        project = Project(name=name, description=description, owner_id=owner_id)
        project.add_member(owner_id)
        self._projects[project.id] = project
        self._emit_event(EventType.PROJECT_CREATED, project.id, owner_id, {"project_name": name})
        return project

    def get_project(self, project_id: str) -> Project:
        if project_id not in self._projects:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        return self._projects[project_id]

    def add_project_member(self, project_id: str, user_id: str, actor_id: str) -> None:
        project = self.get_project(project_id)
        self.get_user(user_id)
        if user_id in project.member_ids:
            raise DuplicateMemberError(f"User {user_id} is already a member of project {project_id}")
        project.add_member(user_id)
        self._emit_event(EventType.USER_ADDED_TO_PROJECT, project_id, actor_id, {"user_id": user_id})

    # --- Task Management ---

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
        task = Task(
            title=title,
            description=description,
            project_id=project_id,
            creator_id=creator_id,
            priority=priority,
        )
        self._tasks[task.id] = task
        project.add_task(task.id)
        self._emit_event(EventType.TASK_CREATED, task.id, creator_id, {"project_id": project_id})
        return task

    def get_task(self, task_id: str) -> Task:
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task {task_id} not found")
        return self._tasks[task_id]

    def assign_task(self, task_id: str, user_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        user = self.get_user(user_id)
        if not user.active:
            raise InactiveUserError(f"Cannot assign task to inactive user {user_id}")
        if task.status == TaskStatus.COMPLETED:
            raise InvalidTaskTransitionError("Cannot assign a completed task")
        task.assigned_to = user_id
        self._emit_event(EventType.TASK_ASSIGNED, task_id, actor_id, {"user_id": user_id})

    def add_task_dependency(self, task_id: str, depends_on_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        self.get_task(depends_on_id)
        if task_id == depends_on_id:
            raise TaskDependencyError("Task cannot depend on itself")
        task.add_dependency(depends_on_id)
        if not task.dependencies_satisfied(self._tasks):
            task.status = TaskStatus.BLOCKED
            self._emit_event(EventType.TASK_BLOCKED, task_id, actor_id, {"reason": "dependency_added"})

    def start_task(self, task_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        if not task.dependencies_satisfied(self._tasks):
            raise TaskDependencyError(f"Task {task_id} has unsatisfied dependencies")
        self._transition_task(task, TaskStatus.IN_PROGRESS, actor_id)
        self._emit_event(EventType.TASK_STARTED, task_id, actor_id)

    def complete_task(self, task_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        self._transition_task(task, TaskStatus.COMPLETED, actor_id)
        task.completed_at = __import__("datetime").datetime.utcnow()
        self._emit_event(EventType.TASK_COMPLETED, task_id, actor_id)
        self._check_dependent_tasks(task_id, actor_id)
        self._check_project_completion(task.project_id, actor_id)

    def cancel_task(self, task_id: str, actor_id: str) -> None:
        task = self.get_task(task_id)
        self._transition_task(task, TaskStatus.CANCELLED, actor_id)
        self._emit_event(EventType.TASK_CANCELLED, task_id, actor_id)

    # --- Internal Methods ---

    def _transition_task(self, task: Task, new_status: TaskStatus, actor_id: str) -> None:
        if not Workflow.can_transition(task.status, new_status):
            raise InvalidTaskTransitionError(
                f"Cannot transition task {task.id} from {task.status} to {new_status}"
            )
        task.status = new_status

    def _check_dependent_tasks(self, completed_task_id: str, actor_id: str) -> None:
        for task in self._tasks.values():
            if completed_task_id in task.dependency_ids and task.dependencies_satisfied(self._tasks):
                if task.status in (TaskStatus.BLOCKED, TaskStatus.TODO):
                    task.status = TaskStatus.READY
                    self._emit_event(EventType.TASK_READY, task.id, actor_id, {"reason": "dependencies_satisfied"})

    def _check_project_completion(self, project_id: str, actor_id: str) -> None:
        project = self.get_project(project_id)
        if project.task_ids and all(
            self._tasks[task_id].status == TaskStatus.COMPLETED
            for task_id in project.task_ids
        ):
            project.status = ProjectStatus.COMPLETED

    def _emit_event(
        self,
        event_type: EventType,
        source_entity: str,
        actor_id: str,
        metadata: Optional[dict] = None,
    ) -> None:
        event = Event(
            event_type=event_type,
            source_entity=source_entity,
            actor_id=actor_id,
            metadata=metadata or {},
        )
        self._events.append(event)

    # --- Queries ---

    def get_events(self) -> List[Event]:
        return self._events.copy()

    def get_project_tasks(self, project_id: str) -> List[Task]:
        project = self.get_project(project_id)
        return [self._tasks[task_id] for task_id in project.task_ids]