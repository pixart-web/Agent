"""Test helper: the workspace a fixture row belongs to.

Tenant tables require `workspace_id` (as in the migrated schema), so fixtures that insert
rows directly use the owner's active workspace, creating a personal one for users made
without the registration flow.
"""

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.knowledge import Workspace, WorkspaceMember
from app.models.user import User


def workspace_for(session: Session, user_id: UUID) -> UUID:
    user = session.get(User, user_id)
    if user.active_workspace_id is not None:
        return user.active_workspace_id
    workspace = Workspace(
        name=f"{user.full_name} workspace",
        slug=f"test-{uuid4().hex[:12]}",
        created_by_user_id=user.id,
    )
    session.add(workspace)
    session.flush()
    session.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner",
            created_by_user_id=user.id,
        )
    )
    user.active_workspace_id = workspace.id
    session.flush()
    return workspace.id
