class NEEKAError(Exception):
    """Base exception for NEEKA errors."""


class ProjectNotFoundError(NEEKAError):
    pass


class TaskNotFoundError(NEEKAError):
    pass


class UserNotFoundError(NEEKAError):
    pass


class InvalidTaskTransitionError(NEEKAError):
    pass


class TaskDependencyError(NEEKAError):
    pass


class CircularDependencyError(TaskDependencyError):
    pass


class InactiveUserError(NEEKAError):
    pass


class DuplicateMemberError(NEEKAError):
    pass


class InvalidProjectMembershipError(NEEKAError):
    pass


class AutomationError(NEEKAError):
    pass


class AutomationLoopError(AutomationError):
    pass