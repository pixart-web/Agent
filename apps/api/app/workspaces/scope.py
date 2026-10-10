from uuid import UUID

from sqlalchemy import select

from app.models.user import User


def active_workspace_id(user_id: UUID):
    """Return a scalar SQL expression for the authenticated user's active tenant."""
    return select(User.active_workspace_id).where(User.id == user_id).scalar_subquery()
