class KnowledgeError(Exception):
    """Base error for workspace knowledge operations."""


class KnowledgeNotFoundError(KnowledgeError):
    pass


class KnowledgePermissionError(KnowledgeError):
    pass


class KnowledgeConflictError(KnowledgeError):
    pass
