class WorkflowNotFoundError(Exception):
    """Raised when a workflow resource is absent or not owned by the user."""


class WorkflowConflictError(Exception):
    """Raised when a workflow operation conflicts with current state."""
