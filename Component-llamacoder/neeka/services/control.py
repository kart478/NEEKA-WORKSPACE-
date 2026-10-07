from neeka.brain.engine import NEEKAEngine
from neeka.brain.project import Project
from neeka.brain.task import Task, TaskPriority
from neeka.brain.user import User, UserRole


class ControlService:
    """Application facade used by API routes; business rules remain in NEEKAEngine."""

    def __init__(self, engine: NEEKAEngine) -> None:
        self.engine = engine

    def create_user(self, name: str, email: str, role: UserRole) -> User:
        return self.engine.create_user(name, email, role)

    def update_user(self, user_id: str, **changes) -> User:
        user = self.engine.get_user(user_id)
        for key, value in changes.items():
            if value is not None:
                setattr(user, key, value)
        self.engine.update_user(user)
        return user

    def create_project(self, name: str, description: str, owner_id: str) -> Project:
        return self.engine.create_project(name, description, owner_id)

    def create_task(self, project_id: str, title: str, description: str, creator_id: str, priority: TaskPriority) -> Task:
        return self.engine.create_task(title, description, project_id, creator_id, priority)

    def update_task(self, task_id: str, **changes) -> Task:
        return self.engine.update_task(task_id, **changes)

    def events_for(self, entity_id: str | None = None) -> list:
        events = self.engine.get_events()
        return [event for event in events if entity_id is None or event.source_entity == entity_id]