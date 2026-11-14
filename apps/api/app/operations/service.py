from collections import defaultdict
from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.agent_run import AgentRun
from app.models.approval_request import ApprovalRequest
from app.models.automation import Automation, AutomationRun
from app.models.command import Command
from app.models.integration_account import IntegrationAccount
from app.models.notification import Notification
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_execution import TaskExecution
from app.models.workflow_enums import (
    AgentRunStatus,
    ApprovalStatus,
    CommandStatus,
    IntegrationAccountStatus,
    TaskExecutionStatus,
    TaskStatus,
)
from app.operations.schemas import (
    AnalyticsTotals,
    AnalyticsTrendPoint,
    OperationsAnalytics,
    OperationsOverview,
    RecentExecution,
)


class OperationsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _task_scope(self, workspace_id: UUID):
        return (
            Task.plan_id == Plan.id,
            Plan.command_id == Command.id,
            Command.workspace_id == workspace_id,
        )

    def overview(self, workspace_id: UUID, user_id: UUID) -> OperationsOverview:
        task_join = self._task_scope(workspace_id)
        active_commands = (
            self.db.scalar(
                select(func.count(Command.id)).where(
                    Command.workspace_id == workspace_id,
                    Command.archived_at.is_(None),
                    Command.status.in_(
                        [CommandStatus.PENDING, CommandStatus.PLANNING, CommandStatus.IN_PROGRESS]
                    ),
                )
            )
            or 0
        )
        pending_tasks = (
            self.db.scalar(
                select(func.count(Task.id))
                .join(Plan, task_join[0])
                .join(Command, task_join[1])
                .where(
                    task_join[2],
                    Task.status.in_(
                        [
                            TaskStatus.PENDING,
                            TaskStatus.READY,
                            TaskStatus.RUNNING,
                            TaskStatus.WAITING_APPROVAL,
                            TaskStatus.BLOCKED,
                        ]
                    ),
                )
            )
            or 0
        )
        pending_approvals = (
            self.db.scalar(
                select(func.count(ApprovalRequest.id))
                .join(Task, ApprovalRequest.task_id == Task.id)
                .join(Plan, task_join[0])
                .join(Command, task_join[1])
                .where(task_join[2], ApprovalRequest.status == ApprovalStatus.PENDING)
            )
            or 0
        )
        active_agent_runs = (
            self.db.scalar(
                select(func.count(AgentRun.id))
                .join(Task, AgentRun.task_id == Task.id)
                .join(Plan, task_join[0])
                .join(Command, task_join[1])
                .where(
                    task_join[2],
                    AgentRun.status.in_([AgentRunStatus.PENDING, AgentRunStatus.RUNNING]),
                )
            )
            or 0
        )
        enabled_automations = (
            self.db.scalar(
                select(func.count(Automation.id)).where(
                    Automation.workspace_id == workspace_id, Automation.enabled.is_(True)
                )
            )
            or 0
        )
        connected_integrations = (
            self.db.scalar(
                select(func.count(IntegrationAccount.id)).where(
                    IntegrationAccount.workspace_id == workspace_id,
                    IntegrationAccount.status == IntegrationAccountStatus.CONNECTED,
                )
            )
            or 0
        )
        unread_alerts = (
            self.db.scalar(
                select(func.count(Notification.id)).where(
                    Notification.workspace_id == workspace_id,
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
            or 0
        )
        recent = self.db.scalars(
            select(TaskExecution)
            .join(Task, TaskExecution.task_id == Task.id)
            .join(Plan, task_join[0])
            .join(Command, task_join[1])
            .where(task_join[2])
            .order_by(TaskExecution.created_at.desc())
            .limit(8)
        ).all()
        return OperationsOverview(
            active_commands=active_commands,
            pending_tasks=pending_tasks,
            pending_approvals=pending_approvals,
            active_agent_runs=active_agent_runs,
            enabled_automations=enabled_automations,
            connected_integrations=connected_integrations,
            unread_alerts=unread_alerts,
            recent_executions=[RecentExecution.model_validate(item) for item in recent],
        )

    def analytics(self, workspace_id: UUID, period_days: int) -> OperationsAnalytics:
        cutoff = utc_now() - timedelta(days=period_days - 1)
        task_scope = self._task_scope(workspace_id)
        commands = self.db.scalars(
            select(Command).where(
                Command.workspace_id == workspace_id, Command.created_at >= cutoff
            )
        ).all()
        agent_runs = self.db.scalars(
            select(AgentRun)
            .join(Task, AgentRun.task_id == Task.id)
            .join(Plan, task_scope[0])
            .join(Command, task_scope[1])
            .where(task_scope[2], AgentRun.created_at >= cutoff)
        ).all()
        executions = self.db.scalars(
            select(TaskExecution)
            .join(Task, TaskExecution.task_id == Task.id)
            .join(Plan, task_scope[0])
            .join(Command, task_scope[1])
            .where(task_scope[2], TaskExecution.created_at >= cutoff)
        ).all()
        automation_runs = self.db.scalars(
            select(AutomationRun)
            .join(Automation, AutomationRun.automation_id == Automation.id)
            .where(Automation.workspace_id == workspace_id, AutomationRun.created_at >= cutoff)
        ).all()

        trends: dict[object, dict[str, int]] = defaultdict(
            lambda: {"commands": 0, "agent_runs": 0, "tool_executions": 0, "automation_runs": 0}
        )
        for item in commands:
            trends[item.created_at.date()]["commands"] += 1
        for item in agent_runs:
            trends[item.created_at.date()]["agent_runs"] += 1
        for item in executions:
            trends[item.created_at.date()]["tool_executions"] += 1
        for item in automation_runs:
            trends[item.created_at.date()]["automation_runs"] += 1

        start_date = cutoff.date()
        points = []
        for offset in range(period_days):
            day = start_date + timedelta(days=offset)
            points.append(AnalyticsTrendPoint(date=day, **trends[day]))

        return OperationsAnalytics(
            period_days=period_days,
            totals=AnalyticsTotals(
                commands=len(commands),
                agent_runs=len(agent_runs),
                tool_executions=len(executions),
                successful_tool_executions=sum(
                    item.status == TaskExecutionStatus.SUCCEEDED for item in executions
                ),
                failed_tool_executions=sum(
                    item.status == TaskExecutionStatus.FAILED for item in executions
                ),
                total_tokens=sum(item.total_tokens or 0 for item in agent_runs),
                automation_runs=len(automation_runs),
                successful_automation_runs=sum(
                    item.status == "completed" for item in automation_runs
                ),
                failed_automation_runs=sum(item.status == "failed" for item in automation_runs),
            ),
            trends=points,
        )
