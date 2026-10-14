import csv
import io
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.models.knowledge import Workspace, WorkspaceInvitation, WorkspaceMember
from app.models.notification import Notification
from app.models.user import User
from app.models.workflow_enums import ActorType
from app.services.audit_service import AuditService
from app.services.data_portability_service import DataPortabilityService

router = APIRouter(prefix="/data-portability", tags=["data-portability"])
Resource = Literal["all", "organizations", "contacts", "projects", "tasks", "activities"]


class RetentionExecution(BaseModel):
    confirmation: Literal["DELETE_EXPIRED_TRANSIENT_DATA"]


def _authorize(db: Session, user: User) -> WorkspaceMember:
    if user.active_workspace_id is None:
        raise HTTPException(status_code=409, detail="No active workspace")
    membership = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == user.active_workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if membership is None or membership.role not in {"owner", "admin"}:
        raise HTTPException(
            status_code=403, detail="Workspace owner or admin permission is required"
        )
    return membership


def _csv_value(value: object) -> str:
    text = (
        json.dumps(value, ensure_ascii=False)
        if isinstance(value, (dict, list))
        else str(value or "")
    )
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


def _retention_preview(db: Session, workspace_id: UUID) -> dict[str, object]:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:  # pragma: no cover - active membership guarantees it
        raise HTTPException(status_code=404, detail="Workspace not found")
    cutoff = datetime.now(UTC) - timedelta(days=workspace.retention_days)
    read_notifications = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.workspace_id == workspace.id,
            Notification.read_at.is_not(None),
            Notification.created_at < cutoff,
        )
    ) or 0
    closed_invitations = db.scalar(
        select(func.count(WorkspaceInvitation.id)).where(
            WorkspaceInvitation.workspace_id == workspace.id,
            WorkspaceInvitation.status.in_(("expired", "revoked")),
            WorkspaceInvitation.created_at < cutoff,
        )
    ) or 0
    return {
        "retention_days": workspace.retention_days,
        "cutoff": cutoff.isoformat(),
        "eligible": {
            "read_notifications": read_notifications,
            "closed_invitations": closed_invitations,
        },
        "preserved": [
            "audit_logs",
            "commands_and_execution_history",
            "crm_records",
            "projects_and_tasks",
            "knowledge_documents",
            "backup_snapshots",
        ],
    }


@router.get("/retention/preview")
def preview_retention(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    membership = _authorize(db, user)
    if membership.role != "owner":
        raise HTTPException(status_code=403, detail="Workspace owner permission is required")
    return _retention_preview(db, membership.workspace_id)


@router.post("/retention/execute")
def execute_retention(
    value: RetentionExecution,
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, object]:
    del value  # Pydantic validates the exact operator confirmation phrase.
    membership = _authorize(db, user)
    if membership.role != "owner":
        raise HTTPException(status_code=403, detail="Workspace owner permission is required")
    preview = _retention_preview(db, membership.workspace_id)
    cutoff = datetime.fromisoformat(str(preview["cutoff"]))
    notifications = db.execute(
        delete(Notification).where(
            Notification.workspace_id == membership.workspace_id,
            Notification.read_at.is_not(None),
            Notification.created_at < cutoff,
        )
    ).rowcount
    invitations = db.execute(
        delete(WorkspaceInvitation).where(
            WorkspaceInvitation.workspace_id == membership.workspace_id,
            WorkspaceInvitation.status.in_(("expired", "revoked")),
            WorkspaceInvitation.created_at < cutoff,
        )
    ).rowcount
    correlation_id = uuid4()
    AuditService(db).record(
        actor_type=ActorType.USER,
        actor_id=user.id,
        event_type="workspace_retention_executed",
        resource_type="workspace",
        resource_id=membership.workspace_id,
        metadata={
            "cutoff": cutoff.isoformat(),
            "read_notifications_deleted": notifications,
            "closed_invitations_deleted": invitations,
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return {
        "cutoff": cutoff.isoformat(),
        "deleted": {
            "read_notifications": notifications,
            "closed_invitations": invitations,
        },
        "audit_correlation_id": str(correlation_id),
    }


@router.get("/export")
def export_workspace_data(
    user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    resource: Resource = "all",
    export_format: Annotated[Literal["json", "csv"], Query(alias="format")] = "json",
) -> Response:
    _authorize(db, user)
    if export_format == "csv" and resource == "all":
        raise HTTPException(status_code=422, detail="CSV export requires a single resource")
    workspace_id = user.active_workspace_id
    assert workspace_id is not None
    service = DataPortabilityService(db, workspace_id)
    data = service.export(resource)
    exported_at = datetime.now(UTC)
    correlation_id = uuid4()
    AuditService(db).record(
        actor_type=ActorType.USER,
        actor_id=user.id,
        event_type="workspace_data_exported",
        resource_type="workspace",
        resource_id=workspace_id,
        metadata={"resource": resource, "format": export_format},
        correlation_id=correlation_id,
    )
    db.commit()
    stem = f"kiko-workspace-{workspace_id}-{exported_at.date().isoformat()}"
    if export_format == "json":
        payload = {
            "schema_version": "1.0",
            "exported_at": exported_at.isoformat(),
            "workspace": service.workspace(),
            "resources": data,
        }
        return Response(
            json.dumps(payload, ensure_ascii=False, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{stem}.json"'},
        )
    rows = data[resource]
    output = io.StringIO()
    fields = list(rows[0]) if rows else ["id"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows([{key: _csv_value(value) for key, value in row.items()} for row in rows])
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{stem}-{resource}.csv"'},
    )
