"""SQLAlchemy models."""

from app.models.agent import Agent
from app.models.agent_run import AgentRun
from app.models.approval_request import ApprovalRequest
from app.models.audit_log import AuditLog
from app.models.automation import Automation, AutomationRun
from app.models.calendar_reference import CalendarReference
from app.models.calendar_write_record import CalendarWriteRecord
from app.models.client_management import (
    CrmClient,
    CrmOpportunity,
    CrmPipeline,
    CrmPipelineStage,
    CrmProject,
    CrmRecordHistory,
    CrmTaskLink,
)
from app.models.codex_run import CodexRun
from app.models.command import Command
from app.models.crm import (
    CrmActivity,
    CrmAddress,
    CrmContact,
    CrmContactMethod,
    CrmContactTag,
    CrmNote,
    CrmOrganization,
    CrmOrganizationMember,
    CrmOrganizationTag,
    CrmTag,
)
from app.models.email_reference import EmailReference
from app.models.email_send_record import EmailSendRecord
from app.models.integration_account import IntegrationAccount
from app.models.integration_oauth_state import IntegrationOAuthState
from app.models.marketing import (
    MarketingAsset,
    MarketingCampaign,
    MarketingContent,
    MarketingContentHistory,
    MarketingPerformanceMetric,
    MarketingPublication,
)
from app.models.outbox_event import OutboxEvent
from app.models.plan import Plan
from app.models.refresh_token import RefreshToken
from app.models.supervisor_run import SupervisorRun
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.task_dependency import TaskDependency
from app.models.task_execution import TaskExecution
from app.models.task_status_history import TaskStatusHistory
from app.models.user import User

__all__ = [
    "AgentRun",
    "Agent",
    "CalendarReference",
    "CalendarWriteRecord",
    "Command",
    "CrmActivity",
    "CrmAddress",
    "CrmClient",
    "CrmContact",
    "CrmContactMethod",
    "CrmContactTag",
    "CrmNote",
    "CrmOpportunity",
    "CrmOrganization",
    "CrmOrganizationMember",
    "CrmOrganizationTag",
    "CrmPipeline",
    "CrmPipelineStage",
    "CrmProject",
    "CrmRecordHistory",
    "CrmTag",
    "CrmTaskLink",
    "EmailReference",
    "EmailSendRecord",
    "IntegrationAccount",
    "IntegrationOAuthState",
    "ApprovalRequest",
    "AuditLog",
    "Automation",
    "AutomationRun",
    "CodexRun",
    "Plan",
    "RefreshToken",
    "MarketingAsset",
    "MarketingCampaign",
    "MarketingContent",
    "MarketingContentHistory",
    "MarketingPerformanceMetric",
    "MarketingPublication",
    "OutboxEvent",
    "SupervisorRun",
    "Task",
    "TaskStatusHistory",
    "User",
    "TaskAction",
    "TaskDependency",
    "TaskExecution",
]
