"""Explicit, tenant-scoped workspace exports.

The allowlists in this module are intentional: credentials, OAuth material, auth
sessions and integration payloads must never enter a portability archive.
"""

from collections.abc import Callable
from datetime import date, datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.command import Command
from app.models.crm import CrmActivity, CrmContact, CrmOrganization
from app.models.knowledge import Workspace
from app.models.plan import Plan
from app.models.project import Project, ProjectActivity
from app.models.task import Task

MAX_EXPORT_ROWS_PER_RESOURCE = 10_000


def _value(value: object) -> object:
    if isinstance(value, (UUID, date, datetime, Enum)):
        return str(value.value if isinstance(value, Enum) else value)
    return value


def _row(instance: object, fields: tuple[str, ...]) -> dict[str, object]:
    return {field: _value(getattr(instance, field)) for field in fields}


class DataPortabilityService:
    """Build a bounded export without serialising ORM objects dynamically."""

    def __init__(self, session: Session, workspace_id: UUID) -> None:
        self.session = session
        self.workspace_id = workspace_id

    def export(self, resource: str) -> dict[str, list[dict[str, object]]]:
        exporters: dict[str, Callable[[], list[dict[str, object]]]] = {
            "organizations": self._organizations,
            "contacts": self._contacts,
            "projects": self._projects,
            "tasks": self._tasks,
            "activities": self._activities,
        }
        if resource == "all":
            return {name: exporter() for name, exporter in exporters.items()}
        return {resource: exporters[resource]()}

    def workspace(self) -> dict[str, object]:
        item = self.session.get(Workspace, self.workspace_id)
        if item is None:  # pragma: no cover - guarded by authenticated membership
            return {}
        return _row(
            item,
            (
                "id", "name", "slug", "description", "primary_objectives", "sector",
                "country", "website", "branding", "retention_days", "status",
                "created_at", "updated_at",
            ),
        )

    def _limited(self, statement: object) -> list[object]:
        return list(self.session.scalars(statement.limit(MAX_EXPORT_ROWS_PER_RESOURCE)))

    def _organizations(self) -> list[dict[str, object]]:
        items = self._limited(
            select(CrmOrganization)
            .where(CrmOrganization.workspace_id == self.workspace_id)
            .order_by(CrmOrganization.created_at)
        )
        fields = ("id", "name", "website", "status", "source", "created_at", "updated_at")
        return [_row(item, fields) for item in items]

    def _contacts(self) -> list[dict[str, object]]:
        items = self._limited(
            select(CrmContact)
            .where(CrmContact.workspace_id == self.workspace_id)
            .order_by(CrmContact.created_at)
        )
        fields = (
            "id", "organization_id", "full_name", "job_title", "website", "status",
            "source", "created_at", "updated_at",
        )
        return [_row(item, fields) for item in items]

    def _projects(self) -> list[dict[str, object]]:
        items = self._limited(
            select(Project)
            .where(Project.workspace_id == self.workspace_id)
            .order_by(Project.created_at)
        )
        fields = (
            "id", "owner_user_id", "client_id", "name", "description", "status",
            "starts_on", "due_on", "created_at", "updated_at",
        )
        return [_row(item, fields) for item in items]

    def _tasks(self) -> list[dict[str, object]]:
        items = self._limited(
            select(Task)
            .join(Plan, Plan.id == Task.plan_id)
            .join(Command, Command.id == Plan.command_id)
            .where(Command.workspace_id == self.workspace_id)
            .order_by(Task.created_at)
        )
        fields = (
            "id", "plan_id", "agent_id", "title", "instructions", "status", "priority",
            "risk_level", "sequence", "created_at", "updated_at", "started_at",
            "completed_at", "due_at", "error_message",
        )
        return [_row(item, fields) for item in items]

    def _activities(self) -> list[dict[str, object]]:
        contact_ids = select(CrmContact.id).where(CrmContact.workspace_id == self.workspace_id)
        organization_ids = select(CrmOrganization.id).where(
            CrmOrganization.workspace_id == self.workspace_id
        )
        crm_items = self._limited(
            select(CrmActivity)
            .where(
                or_(
                    CrmActivity.contact_id.in_(contact_ids),
                    CrmActivity.organization_id.in_(organization_ids),
                )
            )
            .order_by(CrmActivity.created_at)
        )
        crm_fields = (
            "id", "contact_id", "organization_id", "activity_type", "subject", "details",
            "source", "occurred_at", "created_at",
        )
        rows = [dict(_row(item, crm_fields), activity_scope="crm") for item in crm_items]
        project_items = self._limited(
            select(ProjectActivity)
            .join(Project, Project.id == ProjectActivity.project_id)
            .where(Project.workspace_id == self.workspace_id)
            .order_by(ProjectActivity.created_at)
        )
        project_fields = (
            "id", "project_id", "actor_user_id", "event_type", "description", "created_at",
        )
        rows.extend(
            dict(_row(item, project_fields), activity_scope="project")
            for item in project_items
        )
        return rows
