from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user, get_current_user, oauth2_scheme
from app.db.session import get_db
from app.models.knowledge import WorkspaceMember

READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
READ_ONLY_ROLES = frozenset({"viewer"})


def require_workspace_editor(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Refuse writes from read-only members of the caller's active workspace.

    Applied at router level to workspace-scoped routers. Reads pass through untouched; for
    writes the caller is authenticated here (the route authenticates again, cheaply) and a
    `viewer` membership in the active workspace gets 403. Missing memberships are left to
    the route, which answers 404 without revealing the workspace.
    """
    if request.method in READ_METHODS:
        return
    user = get_current_active_user(get_current_user(token, db))
    if user.active_workspace_id is None:
        return
    role = db.scalar(
        select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == user.active_workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if role in READ_ONLY_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace edit permission is required",
        )
