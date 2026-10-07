# brain/exceptions.py
class NEEKAError(Exception):
    """Base exception for all NEEKA errors."""


class ProjectNotFoundError(NEEKAError):
    """Raised when a project cannot be found."""


class TaskNotFoundError(NEEKAError):
    """Raised when a task cannot be found."""


class UserNotFoundError(NEEKAError):
    """Raised when a user cannot be found."""


class InvalidTaskTransitionError(NEEKAError):
    """Raised when a task state transition is not allowed."""


class TaskDependencyError(NEEKAError):
    """Raised when a task dependency is violated."""


class InactiveUserError(NEEKAError):
    """Raised when an inactive user is assigned work."""


class DuplicateMemberError(NEEKAError):
    """Raised when a user is added to a project twice."""