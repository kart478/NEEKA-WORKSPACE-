class KnowledgeError(Exception):
    """Base knowledge domain error."""


class KnowledgeNotFoundError(KnowledgeError):
    pass


class KnowledgePermissionError(KnowledgeError):
    pass
