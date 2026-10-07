import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from neeka.brain.exceptions import (
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
    WorkflowNotFoundError,
)

logger = logging.getLogger(__name__)


def error_code(error: Exception) -> str:
    codes = {
        UserNotFoundError: "user_not_found", ProjectNotFoundError: "project_not_found",
        TaskNotFoundError: "task_not_found", CircularDependencyError: "circular_dependency",
        EventNotFoundError: "event_not_found", AutomationExecutionNotFoundError: "execution_not_found",
        WorkflowNotFoundError: "workflow_not_found",
        TaskDependencyError: "task_dependency_error", InvalidTaskTransitionError: "invalid_transition",
        InvalidProjectMembershipError: "invalid_project_membership", DuplicateMemberError: "duplicate_member",
        InactiveUserError: "inactive_user",
    }
    return codes.get(type(error), "bad_request")


async def neeka_error_handler(_request: Request, error: Exception) -> JSONResponse:
    status = 409 if isinstance(error, (CircularDependencyError, DuplicateMemberError, InvalidTaskTransitionError)) else 404 if isinstance(
        error, (UserNotFoundError, ProjectNotFoundError, TaskNotFoundError, EventNotFoundError,
            AutomationExecutionNotFoundError, WorkflowNotFoundError)
    ) else 400
    return JSONResponse(status_code=status, content={"error": error_code(error), "message": str(error)})


async def internal_error_handler(_request: Request, error: Exception) -> JSONResponse:
    logger.exception("Unhandled API error", exc_info=error)
    return JSONResponse(status_code=500, content={"error": "internal_error", "message": "Internal server error"})