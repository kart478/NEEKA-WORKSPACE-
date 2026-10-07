from enum import Enum

from .exceptions import ApprovalRequiredError, UnauthorizedIntelligenceAction


class PermissionMode(str, Enum):
    READ_ONLY = "READ_ONLY"
    ASSISTED = "ASSISTED"
    AUTONOMOUS = "AUTONOMOUS"


def authorize(mode: PermissionMode, write: bool, approved: bool = False) -> None:
    if not write:
        return
    if mode == PermissionMode.READ_ONLY:
        raise UnauthorizedIntelligenceAction("READ_ONLY mode cannot modify NEEKA state")
    if mode == PermissionMode.ASSISTED and not approved:
        raise ApprovalRequiredError("This action requires explicit approval in ASSISTED mode")