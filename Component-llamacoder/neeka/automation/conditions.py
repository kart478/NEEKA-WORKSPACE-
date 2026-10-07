from collections.abc import Mapping

from neeka.brain.task import Task, TaskStatus
from neeka.brain.user import User


def all_dependencies_completed(task: Task, tasks: Mapping[str, Task]) -> bool:
    return bool(task.dependency_ids) and all(
        tasks[dependency_id].status == TaskStatus.COMPLETED
        for dependency_id in task.dependency_ids
    )


def user_is_active(user: User) -> bool:
    return user.active