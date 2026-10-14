from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.approval_request import ApprovalRequest
from app.models.automation import Automation, AutomationRun
from app.models.command import Command
from app.models.integration_account import IntegrationAccount
from app.models.notification import Notification, NotificationPreference
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_execution import TaskExecution
from app.models.workflow_enums import ApprovalStatus, IntegrationAccountStatus, TaskExecutionStatus
from app.notifications.schemas import (
    NotificationList,
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    NotificationRead,
)

DEFAULT_KINDS = [
    "approval_required",
    "execution_failed",
    "integration_disconnected",
    "automation_failed",
]


class NotificationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self, user_id: UUID, workspace_id: UUID, *, unread_only: bool = False
    ) -> NotificationList:
        preferences = self._preferences(user_id)
        if preferences.in_app_enabled:
            self._reconcile(user_id, workspace_id, set(preferences.enabled_kinds or DEFAULT_KINDS))
        query = select(Notification).where(
            Notification.user_id == user_id,
            Notification.workspace_id == workspace_id,
        )
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        values = list(
            self.session.scalars(query.order_by(Notification.created_at.desc()).limit(100))
        )
        unread = (
            self.session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.user_id == user_id,
                    Notification.workspace_id == workspace_id,
                    Notification.read_at.is_(None),
                )
            )
            or 0
        )
        return NotificationList(
            notifications=[
                NotificationRead.model_validate(item, from_attributes=True) for item in values
            ],
            unread_count=unread,
        )

    def mark_read(self, user_id: UUID, workspace_id: UUID, notification_id: UUID) -> None:
        item = self.session.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.workspace_id == workspace_id,
            )
        )
        if item is None:
            raise LookupError
        item.read_at = utc_now()
        self.session.commit()

    def mark_all_read(self, user_id: UUID, workspace_id: UUID) -> None:
        values = self.session.scalars(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.workspace_id == workspace_id,
                Notification.read_at.is_(None),
            )
        )
        now = utc_now()
        for item in values:
            item.read_at = now
        self.session.commit()

    def preferences(self, user_id: UUID) -> NotificationPreferenceRead:
        return self._preference_output(self._preferences(user_id))

    def update_preferences(
        self, user_id: UUID, value: NotificationPreferenceUpdate
    ) -> NotificationPreferenceRead:
        preference = self._preferences(user_id)
        preference.in_app_enabled = value.in_app_enabled
        preference.email_enabled = value.email_enabled
        preference.enabled_kinds = value.enabled_kinds
        self.session.commit()
        return self._preference_output(preference)

    def _preferences(self, user_id: UUID) -> NotificationPreference:
        value = self.session.get(NotificationPreference, user_id)
        if value is None:
            value = NotificationPreference(user_id=user_id, enabled_kinds=DEFAULT_KINDS)
            self.session.add(value)
            self.session.commit()
        return value

    def _reconcile(self, user_id: UUID, workspace_id: UUID, kinds: set[str]) -> None:
        events: list[dict[str, object]] = []
        if "approval_required" in kinds:
            approvals = self.session.execute(
                select(ApprovalRequest.id, ApprovalRequest.title, ApprovalRequest.requested_at)
                .join(Task, Task.id == ApprovalRequest.task_id)
                .join(Plan, Plan.id == Task.plan_id)
                .join(Command, Command.id == Plan.command_id)
                .where(
                    Command.workspace_id == workspace_id,
                    ApprovalRequest.status == ApprovalStatus.PENDING,
                )
            )
            events.extend(
                dict(
                    event_key=f"approval:{item.id}",
                    kind="approval_required",
                    title="Approval required",
                    body=item.title,
                    href="/dashboard/approvals",
                    created_at=item.requested_at,
                )
                for item in approvals
            )
        if "execution_failed" in kinds:
            executions = self.session.execute(
                select(TaskExecution.id, Task.title, TaskExecution.created_at)
                .join(Task, Task.id == TaskExecution.task_id)
                .join(Plan, Plan.id == Task.plan_id)
                .join(Command, Command.id == Plan.command_id)
                .where(
                    Command.workspace_id == workspace_id,
                    TaskExecution.status == TaskExecutionStatus.FAILED,
                )
            )
            events.extend(
                dict(
                    event_key=f"execution:{item.id}",
                    kind="execution_failed",
                    title="Execution failed",
                    body=item.title,
                    href="/dashboard/executions",
                    created_at=item.created_at,
                )
                for item in executions
            )
        if "automation_failed" in kinds:
            runs = self.session.execute(
                select(AutomationRun.id, Automation.name, AutomationRun.created_at)
                .join(Automation, Automation.id == AutomationRun.automation_id)
                .where(Automation.workspace_id == workspace_id, AutomationRun.status == "failed")
            )
            events.extend(
                dict(
                    event_key=f"automation:{item.id}",
                    kind="automation_failed",
                    title="Automation failed",
                    body=item.name,
                    href="/dashboard/automations",
                    created_at=item.created_at,
                )
                for item in runs
            )
        if "integration_disconnected" in kinds:
            accounts = self.session.execute(
                select(
                    IntegrationAccount.id,
                    IntegrationAccount.provider,
                    IntegrationAccount.updated_at,
                ).where(
                    IntegrationAccount.workspace_id == workspace_id,
                    IntegrationAccount.status != IntegrationAccountStatus.CONNECTED,
                )
            )
            events.extend(
                dict(
                    event_key=f"integration:{item.id}:{item.updated_at.isoformat()}",
                    kind="integration_disconnected",
                    title="Integration requires attention",
                    body=item.provider,
                    href="/dashboard/integrations",
                    created_at=item.updated_at,
                )
                for item in accounts
            )
        for event in events:
            self.session.add(Notification(user_id=user_id, workspace_id=workspace_id, **event))
            try:
                self.session.commit()
            except IntegrityError:
                self.session.rollback()

    @staticmethod
    def _preference_output(value: NotificationPreference) -> NotificationPreferenceRead:
        return NotificationPreferenceRead(
            in_app_enabled=value.in_app_enabled,
            email_enabled=value.email_enabled,
            enabled_kinds=value.enabled_kinds,
        )
