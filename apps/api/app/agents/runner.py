import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents.context import AgentContextBuilder, AgentTaskContext
from app.agents.exceptions import AgentProposalError
from app.agents.registry import SpecializedAgentRegistry, build_agent_registry
from app.ai.base import LLMProvider, LLMResult
from app.ai.exceptions import AIError
from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.execution.context_safety import sanitize_execution_payload
from app.execution.policies import ExecutionRiskPolicy, action_fingerprint, maximum_risk
from app.execution.registry import ToolRegistry
from app.execution.tools.registry import build_tool_registry
from app.models.agent_run import AgentRun
from app.models.command import Command
from app.models.plan import Plan
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.workflow_enums import (
    TERMINAL_COMMAND_STATUSES,
    ActorType,
    AgentRunStatus,
    CommandStatus,
    PlanStatus,
    TaskActionStatus,
    TaskStatus,
)
from app.repositories.agent_repository import AgentRepository
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.execution_repository import ExecutionRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.specialized_agent import AgentProposal
from app.services.audit_service import AuditService
from app.services.dependency_service import DependencyService
from app.services.execution_service import ExecutionService
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentRunnerResult:
    run: AgentRun
    actions: list[TaskAction]


class AgentRunnerService:
    def __init__(
        self,
        session: Session,
        provider: LLMProvider,
        *,
        settings: Settings | None = None,
        agent_registry: SpecializedAgentRegistry | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.settings = settings or get_settings()
        self.registry = agent_registry or build_agent_registry()
        self.tools = tool_registry or build_tool_registry()
        self.tasks = TaskRepository(session)
        self.runs = AgentRunRepository(session)
        self.agents = AgentRepository(session)
        self.actions = ExecutionRepository(session)
        self.dependencies = DependencyService(session)
        self.audit = AuditService(session)
        self.risk_policy = ExecutionRiskPolicy()
        self.context_builder = AgentContextBuilder(session)

    def run(self, task_id: UUID, user_id: UUID) -> AgentRunnerResult:
        context, run_id = self._start(task_id, user_id, feedback=None, rerun=False)
        return self._call_and_persist(context, run_id, user_id)

    def rerun(self, task_id: UUID, user_id: UUID, feedback: str | None) -> AgentRunnerResult:
        if feedback and len(feedback) > self.settings.agent_max_feedback_chars:
            raise WorkflowConflictError("Feedback exceeds the configured limit")
        context, run_id = self._start(task_id, user_id, feedback=feedback, rerun=True)
        return self._call_and_persist(context, run_id, user_id)

    def _start(
        self, task_id: UUID, user_id: UUID, *, feedback: str | None, rerun: bool
    ) -> tuple[AgentTaskContext, UUID]:
        try:
            task = self.tasks.get_owned_for_update(task_id, user_id)
            if task is None:
                raise WorkflowNotFoundError("Task not found")
            if task.status != TaskStatus.READY:
                raise WorkflowConflictError("Only a ready task can run its assigned agent")
            if not self.dependencies.satisfied(task.id):
                raise WorkflowConflictError("Task dependencies are not completed")
            plan = self.session.get(Plan, task.plan_id)
            command = self.session.scalar(
                select(Command)
                .where(Command.id == plan.command_id, Command.user_id == user_id)
                .with_for_update(of=Command)
            )
            if command.status in TERMINAL_COMMAND_STATUSES or plan.status in {
                PlanStatus.COMPLETED,
                PlanStatus.FAILED,
                PlanStatus.CANCELLED,
            }:
                raise WorkflowConflictError("Command or plan is terminal")
            if self.runs.has_active(task.id):
                raise WorkflowConflictError("An agent run is already active for this task")
            agent = self.registry.get(task.agent_id)
            persisted_agent = self.agents.get(task.agent_id)
            if persisted_agent is None or persisted_agent.status != "ready":
                raise WorkflowConflictError("Assigned agent is unavailable")
            previous_runs = self.runs.list_for_task_owned(task.id, user_id)
            previous_actions = self.actions.list_actions_for_task_owned(task.id, user_id)
            if rerun:
                failed = bool(previous_runs and previous_runs[0].status == AgentRunStatus.FAILED)
                actions_reset = bool(previous_actions) and all(
                    action.status == TaskActionStatus.CANCELLED for action in previous_actions
                )
                if not (failed or actions_reset or (feedback and feedback.strip())):
                    raise WorkflowConflictError(
                        "Agent rerun requires failure, reset actions, or feedback"
                    )
            elif previous_runs:
                raise WorkflowConflictError("Use rerun-agent to preserve the previous run history")
            if command.correlation_id is None:
                command.correlation_id = uuid4()
            context = self.context_builder.build(
                task,
                user_id,
                agent.allowed_tools,
                feedback,
                self.settings.agent_max_context_chars,
            )
            run = AgentRun(
                task_id=task.id,
                agent_id=agent.agent_id,
                user_id=user_id,
                status=AgentRunStatus.RUNNING,
                provider=self.provider.provider_name,
                model=self.provider.model_name,
                prompt_version=agent.prompt_version,
                user_feedback=feedback,
                correlation_id=command.correlation_id,
            )
            self.runs.add(run)
            self.session.flush()
            self.audit.record(
                actor_type=ActorType.AGENT,
                actor_id=None,
                event_type="agent_run_started",
                resource_type="agent_run",
                resource_id=run.id,
                metadata={"task_id": str(task.id), "agent_id": agent.agent_id},
                correlation_id=run.correlation_id,
            )
            run_id = run.id
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise WorkflowConflictError("An agent run is already active for this task") from error
        except Exception:
            self.session.rollback()
            raise
        logger.info("agent_run_started", extra=self._log(run))
        return context, run_id

    def _call_and_persist(
        self, context: AgentTaskContext, run_id: UUID, user_id: UUID
    ) -> AgentRunnerResult:
        agent = self.registry.get(self.session.get(AgentRun, run_id).agent_id)
        try:
            result = agent.propose_actions(context=context, provider=self.provider)
            proposal = self._validate(result.data, context, agent)
            return self._persist(run_id, user_id, proposal, result)
        except Exception as error:
            self._mark_failed(run_id, user_id, error)
            if isinstance(error, (AIError, WorkflowConflictError, AgentProposalError)):
                raise
            raise AgentProposalError("Specialized agent proposal failed validation") from error

    def _validate(self, proposal: AgentProposal, context: AgentTaskContext, agent) -> AgentProposal:
        maximum = min(self.settings.agent_max_actions_per_task, agent.max_actions_per_task)
        if len(proposal.actions) > maximum:
            raise AgentProposalError("Agent proposed too many actions")
        validated = []
        task = self.session.get(Task, context.task_id)
        for item in sorted(proposal.actions, key=lambda action: action.sequence):
            if item.tool_name not in agent.allowed_tools:
                raise AgentProposalError("Agent proposed a tool outside its allowlist")
            definition = self.tools.get(item.tool_name, item.tool_version)
            payload = self.tools.validate_input(definition, item.input_payload, agent.agent_id)
            risk = maximum_risk(
                task.risk_level,
                item.risk_level,
                definition.risk_level,
                self.risk_policy.evaluate(item.input_payload),
            )
            validated.append(
                item.model_copy(
                    update={
                        "input_payload": payload.model_dump(mode="json"),
                        "risk_level": risk,
                    }
                )
            )
        return proposal.model_copy(update={"actions": validated})

    def _persist(
        self,
        run_id: UUID,
        user_id: UUID,
        proposal: AgentProposal,
        result: LLMResult[AgentProposal],
    ) -> AgentRunnerResult:
        try:
            run = self.runs.get_owned_for_update(run_id, user_id)
            task = self.tasks.get_owned_for_update(run.task_id, user_id)
            plan = self.session.get(Plan, task.plan_id)
            command = self.session.get(Command, plan.command_id)
            if run.status != AgentRunStatus.RUNNING:
                raise WorkflowConflictError("Agent run is no longer active")
            if command.status == CommandStatus.CANCELLED or task.status != TaskStatus.READY:
                run.status = AgentRunStatus.CANCELLED
                run.completed_at = utc_now()
                self.session.commit()
                raise WorkflowConflictError("Task was cancelled or changed during agent analysis")
            agent = self.registry.get(run.agent_id)
            actions: list[TaskAction] = []
            for item in proposal.actions:
                definition = self.tools.get(item.tool_name, item.tool_version)
                payload = sanitize_execution_payload(item.input_payload)
                action = TaskAction(
                    task_id=task.id,
                    tool_name=definition.name,
                    tool_version=definition.version,
                    input_payload=payload,
                    risk_level=item.risk_level,
                    status=TaskActionStatus.PROPOSED,
                    created_by_type=ActorType.AGENT,
                    created_by_id=None,
                    action_fingerprint=action_fingerprint(
                        definition.name, definition.version, payload, item.risk_level
                    ),
                    correlation_id=run.correlation_id,
                )
                self.actions.add_action(action)
                self.session.flush()
                actions.append(action)
                self.audit.record(
                    actor_type=ActorType.AGENT,
                    actor_id=None,
                    event_type="agent_action_proposed",
                    resource_type="task_action",
                    resource_id=action.id,
                    metadata={
                        "agent_id": agent.agent_id,
                        "run_id": str(run.id),
                        "sequence": item.sequence,
                        "reason": item.reason[:500],
                        "expected_outcome": item.expected_outcome[:500],
                    },
                    correlation_id=run.correlation_id,
                )
            run.status = AgentRunStatus.COMPLETED
            run.proposal_summary = proposal.summary
            run.provider = result.provider
            run.model = result.model
            run.input_tokens = result.input_tokens
            run.output_tokens = result.output_tokens
            run.total_tokens = result.total_tokens
            run.latency_ms = result.latency_ms
            run.completed_at = utc_now()
            self.audit.record(
                actor_type=ActorType.AGENT,
                actor_id=None,
                event_type="agent_run_completed",
                resource_type="agent_run",
                resource_id=run.id,
                metadata={
                    "task_id": str(task.id),
                    "agent_id": run.agent_id,
                    "actions": len(actions),
                },
                correlation_id=run.correlation_id,
            )
            self.session.commit()
            for action in actions:
                if not action.tool_name.startswith(("github.", "codex.")):
                    continue
                try:
                    ExecutionService(self.session, self.tools).dispatch(
                        action.id,
                        user_id,
                        actor_type=ActorType.KIKO,
                    )
                except Exception as error:
                    logger.warning(
                        "integration_action_auto_dispatch_failed",
                        extra={"action_id": str(action.id), "error": type(error).__name__},
                    )
        except Exception:
            self.session.rollback()
            raise
        logger.info("agent_run_completed", extra=self._log(run))
        return AgentRunnerResult(run=run, actions=actions)

    def _mark_failed(self, run_id: UUID, user_id: UUID, error: Exception) -> None:
        self.session.rollback()
        run = self.runs.get_owned_for_update(run_id, user_id)
        if run is None or run.status == AgentRunStatus.CANCELLED:
            return
        run.status = AgentRunStatus.FAILED
        run.error_code = type(error).__name__
        run.error_message = (
            str(error)[:500]
            if isinstance(error, (AIError, AgentProposalError))
            else "Agent run failed"
        )
        run.completed_at = utc_now()
        self.audit.record(
            actor_type=ActorType.AGENT,
            actor_id=None,
            event_type="agent_run_failed",
            resource_type="agent_run",
            resource_id=run.id,
            metadata={
                "task_id": str(run.task_id),
                "agent_id": run.agent_id,
                "error_code": run.error_code,
            },
            correlation_id=run.correlation_id,
        )
        self.session.commit()
        logger.info("agent_run_failed", extra=self._log(run))

    @staticmethod
    def _log(run: AgentRun) -> dict[str, object]:
        return {
            "agent_run_id": str(run.id),
            "task_id": str(run.task_id),
            "agent_id": run.agent_id,
            "provider": run.provider,
            "model": run.model,
            "tokens": run.total_tokens,
            "latency": run.latency_ms,
            "correlation_id": str(run.correlation_id),
        }
