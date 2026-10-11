from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.registry import SpecializedAgentRegistry, build_agent_registry
from app.models.agent_configuration import AgentConfiguration
from app.models.agent_run import AgentRun
from app.models.command import Command
from app.models.knowledge import KnowledgeItem, WorkspaceMember
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.task_execution import TaskExecution
from app.models.workflow_enums import ActorType, AgentRunStatus, TaskActionStatus, TaskStatus
from app.repositories.agent_repository import AgentRepository
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.specialized_agent import AgentConfigurationUpdate
from app.services.audit_service import AuditService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError
from app.workspaces.scope import active_workspace_id


class AgentManagementService:
    def __init__(self, session: Session, registry: SpecializedAgentRegistry | None = None) -> None:
        self.session = session
        self.registry = registry or build_agent_registry()
        self.agents = AgentRepository(session)
        self.runs = AgentRunRepository(session)
        self.tasks = TaskRepository(session)
        self.audit = AuditService(session)

    def capabilities(self, agent_id: str, max_actions: int):
        implementation = self.registry.get(agent_id)
        persisted = self.agents.get(agent_id)
        if persisted is None:
            raise WorkflowNotFoundError("Agent not found")
        return {
            "id": implementation.agent_id,
            "name": persisted.name,
            "description": persisted.description,
            "prompt_version": implementation.prompt_version,
            "allowed_tools": sorted(implementation.allowed_tools),
            "default_risk_policy": implementation.default_risk_policy,
            "max_actions": min(max_actions, implementation.max_actions_per_task),
        }

    def list_runs(self, task_id: UUID, user_id: UUID) -> list[AgentRun]:
        if self.tasks.get_owned(task_id, user_id) is None:
            raise WorkflowNotFoundError("Task not found")
        return self.runs.list_for_task_owned(task_id, user_id)

    def overview(self, agent_id: str, user_id: UUID, max_actions: int) -> dict:
        capabilities = self.capabilities(agent_id, max_actions)
        configuration = self.configuration(agent_id, user_id, max_actions)
        counts = dict(
            self.session.execute(
                select(Task.status, func.count(Task.id))
                .join(Plan, Plan.id == Task.plan_id)
                .join(Command, Command.id == Plan.command_id)
                .where(
                    Task.agent_id == agent_id,
                    Command.workspace_id == active_workspace_id(user_id),
                )
                .group_by(Task.status)
            ).all()
        )
        recent = self.runs.recent_for_agent(agent_id, user_id)
        completed = sum(run.status == AgentRunStatus.COMPLETED for run in recent)
        failed = sum(run.status == AgentRunStatus.FAILED for run in recent)
        decided = completed + failed
        return {
            "capabilities": capabilities,
            "tasks_pending": counts.get(TaskStatus.PENDING, 0) + counts.get(TaskStatus.READY, 0),
            "tasks_running": counts.get(TaskStatus.RUNNING, 0),
            "tasks_waiting_approval": counts.get(TaskStatus.WAITING_APPROVAL, 0),
            "tasks_failed": counts.get(TaskStatus.FAILED, 0),
            "recent_runs": recent,
            "completed_runs": completed,
            "failed_runs": failed,
            "success_rate": round(completed / decided * 100, 2) if decided else 0.0,
            "operational_status": "disabled" if not configuration["enabled"] else "operational",
            "operational_message": "Disabled for this workspace"
            if not configuration["enabled"]
            else "Provider available",
            "configuration": configuration,
        }

    def configuration(self, agent_id: str, user_id: UUID, max_actions: int) -> dict:
        capabilities = self.capabilities(agent_id, max_actions)
        workspace_id = self.session.scalar(select(active_workspace_id(user_id)))
        config = self.session.scalar(
            select(AgentConfiguration).where(
                AgentConfiguration.workspace_id == workspace_id,
                AgentConfiguration.agent_id == agent_id,
            )
        )
        return {
            "enabled": config.enabled if config else True,
            "model": config.model if config else None,
            "allowed_tools": config.allowed_tools
            if config and config.allowed_tools is not None
            else capabilities["allowed_tools"],
            "approval_policy": config.approval_policy if config else "platform_default",
            "max_actions_per_task": config.max_actions_per_task
            if config and config.max_actions_per_task
            else capabilities["max_actions"],
            "monthly_token_budget": config.monthly_token_budget if config else None,
            "knowledge_source_ids": [UUID(value) for value in config.knowledge_source_ids]
            if config
            else [],
        }

    def update_configuration(
        self, agent_id: str, user_id: UUID, max_actions: int, data: AgentConfigurationUpdate
    ) -> dict:
        capabilities = self.capabilities(agent_id, max_actions)
        workspace_id = self.session.scalar(select(active_workspace_id(user_id)))
        membership = self.session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if membership is None or membership.role not in {"owner", "admin"}:
            raise PermissionError("Workspace administrator permission is required")
        values = data.model_dump(exclude_unset=True)
        if values.get("allowed_tools") is not None:
            unknown = set(values["allowed_tools"]) - set(capabilities["allowed_tools"])
            if unknown:
                raise WorkflowConflictError("Configuration contains unsupported tools")
        if values.get("knowledge_source_ids") is not None:
            ids = values["knowledge_source_ids"]
            found = set(
                self.session.scalars(
                    select(KnowledgeItem.id).where(
                        KnowledgeItem.workspace_id == workspace_id,
                        KnowledgeItem.id.in_(ids),
                    )
                )
            )
            if found != set(ids):
                raise WorkflowNotFoundError("Knowledge source not found")
            values["knowledge_source_ids"] = [str(value) for value in ids]
        try:
            config = self.session.scalar(
                select(AgentConfiguration).where(
                    AgentConfiguration.workspace_id == workspace_id,
                    AgentConfiguration.agent_id == agent_id,
                )
            )
            if config is None:
                config = AgentConfiguration(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    updated_by_user_id=user_id,
                )
                self.session.add(config)
            for field, value in values.items():
                setattr(config, field, value)
            config.updated_by_user_id = user_id
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return self.configuration(agent_id, user_id, max_actions)

    def reassign(self, task_id: UUID, user_id: UUID, agent_id: str) -> Task:
        try:
            task = self.tasks.get_owned_for_update(task_id, user_id)
            if task is None:
                raise WorkflowNotFoundError("Task not found")
            if task.status not in {TaskStatus.PENDING, TaskStatus.READY, TaskStatus.BLOCKED}:
                raise WorkflowConflictError("Task has already started")
            self.registry.get(agent_id)
            persisted = self.agents.get(agent_id)
            if persisted is None or persisted.status != "ready":
                raise WorkflowNotFoundError("Agent not found")
            if self.runs.has_active(task.id):
                raise WorkflowConflictError("An agent run is active")
            executed = self.session.scalar(
                select(TaskExecution.id)
                .join(TaskAction, TaskAction.id == TaskExecution.task_action_id)
                .where(TaskAction.task_id == task.id)
                .limit(1)
            )
            active_actions = self.session.scalar(
                select(TaskAction.id)
                .where(
                    TaskAction.task_id == task.id,
                    TaskAction.status != TaskActionStatus.CANCELLED,
                )
                .limit(1)
            )
            if executed is not None or active_actions is not None:
                raise WorkflowConflictError("Reset existing actions before reassignment")
            previous = task.agent_id
            task.agent_id = agent_id
            plan = self.session.get(Plan, task.plan_id)
            command = self.session.get(Command, plan.command_id)
            self.audit.record(
                actor_type=ActorType.USER,
                actor_id=user_id,
                event_type="task_agent_reassigned",
                resource_type="task",
                resource_id=task.id,
                metadata={"from_agent": previous, "to_agent": agent_id},
                correlation_id=command.correlation_id,
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        self.session.refresh(task)
        return task
