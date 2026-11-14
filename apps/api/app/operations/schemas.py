from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecentExecution(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    tool_name: str
    status: str
    duration_ms: int | None
    created_at: datetime


class OperationsOverview(BaseModel):
    active_commands: int
    pending_tasks: int
    pending_approvals: int
    active_agent_runs: int
    enabled_automations: int
    connected_integrations: int
    unread_alerts: int
    recent_executions: list[RecentExecution]


class AnalyticsTotals(BaseModel):
    commands: int
    agent_runs: int
    tool_executions: int
    successful_tool_executions: int
    failed_tool_executions: int
    total_tokens: int
    automation_runs: int
    successful_automation_runs: int
    failed_automation_runs: int


class AnalyticsTrendPoint(BaseModel):
    date: date
    commands: int = 0
    agent_runs: int = 0
    tool_executions: int = 0
    automation_runs: int = 0


class OperationsAnalytics(BaseModel):
    period_days: int
    totals: AnalyticsTotals
    estimated_cost_minor: int | None = None
    estimated_cost_currency: str | None = None
    cost_status: str = "unavailable"
    trends: list[AnalyticsTrendPoint]
