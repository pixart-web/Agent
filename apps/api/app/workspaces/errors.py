class WorkspaceError(Exception):
    """Base workspace lifecycle error."""


class WorkspaceNotFoundError(WorkspaceError):
    pass


class WorkspacePermissionError(WorkspaceError):
    pass


class WorkspaceConflictError(WorkspaceError):
    pass


class WorkspaceInvitationError(WorkspaceError):
    pass
