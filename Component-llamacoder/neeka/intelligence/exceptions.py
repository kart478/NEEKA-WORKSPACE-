class IntelligenceError(Exception):
    """Base exception for intelligence-layer failures."""


class InvalidAIResponseError(IntelligenceError):
    pass


class UnauthorizedIntelligenceAction(IntelligenceError):
    pass


class ApprovalRequiredError(IntelligenceError):
    pass


class UnknownToolError(IntelligenceError):
    pass


class ToolValidationError(IntelligenceError):
    pass


class IntelligenceLoopError(IntelligenceError):
    pass