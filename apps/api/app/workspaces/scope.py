from uuid import UUID

from sqlalchemy import and_, or_, select

from app.models.user import User


def active_workspace_id(user_id: UUID):
    """Return a scalar SQL expression for the authenticated user's active tenant."""
    return select(User.active_workspace_id).where(User.id == user_id).scalar_subquery()


def workspace_or_legacy_owner(model, user_id: UUID):
    """Scope a migrating tenant root, retaining only the caller's unbackfilled rows."""
    return or_(
        model.workspace_id == active_workspace_id(user_id),
        and_(model.workspace_id.is_(None), model.user_id == user_id),
    )
