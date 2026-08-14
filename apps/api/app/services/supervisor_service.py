import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.base import LLMProvider, LLMResult
from app.ai.exceptions import AIError, AIInvalidResponseError, SupervisorPlanningError
from app.ai.prompts.supervisor_plan_v1 import (
    PROMPT_VERSION,
    AvailableAgent,
    build_system_prompt,
    build_user_prompt,
)
from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.models.plan import Plan
from app.models.supervisor_run import SupervisorRun
from app.models.task import Task
from app.models.task_status_history import TaskStatusHistory
from app.models.workflow_enums import (
    TERMINAL_COMMAND_STATUSES,
    CommandStatus,
    PlanStatus,
    SupervisorRunStatus,
    TaskStatus,
)
from app.repositories.agent_repository import AgentRepository
from app.repositories.command_repository import CommandRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.supervisor_run_repository import SupervisorRunRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.task_status_history_repository import TaskStatusHistoryRepository
from app.schemas.supervisor import SupervisorPlanProposal
from app.services.agent_assignment_policy import AgentAssignmentPolicy
from app.services.risk_policy import RiskPolicy
from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SupervisorPlanningResult:
    plan: Plan
    tasks: list[Task]
    run: SupervisorRun


@dataclass(frozen=True)
class PlanningContext:
    run_id: UUID
    command_input: str
    agents: list[AvailableAgent]
    previous_plan_summary: str | None
    feedback: str | None


class SupervisorService:
    def __init__(
        self,
        session: Session,
        provider: LLMProvider,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.settings = settings or get_settings()
        self.commands = CommandRepository(session)
        self.plans = PlanRepository(session)
        self.tasks = TaskRepository(session)
        self.history = TaskStatusHistoryRepository(session)
        self.runs = SupervisorRunRepository(session)
        self.agents = AgentRepository(session)
        self.risk_policy = RiskPolicy()
        self.assignment_policy = AgentAssignmentPolicy()

    def generate(self, command_id: UUID, user_id: UUID) -> SupervisorPlanningResult:
        context = self._start(command_id, user_id, feedback=None, regenerate=False)
        return self._call_and_persist(context, command_id, user_id)

    def regenerate(
        self,
        command_id: UUID,
        user_id: UUID,
        feedback: str,
    ) -> SupervisorPlanningResult:
        if len(feedback) > self.settings.supervisor_max_feedback_chars:
            raise WorkflowConflictError("Feedback exceeds the configured limit")
        context = self._start(command_id, user_id, feedback=feedback, regenerate=True)
        return self._call_and_persist(context, command_id, user_id)

    def _start(
        self,
        command_id: UUID,
        user_id: UUID,
        *,
        feedback: str | None,
        regenerate: bool,
    ) -> PlanningContext:
        try:
            command = self.commands.get_owned_for_update(command_id, user_id)
            if command is None:
                raise WorkflowNotFoundError("Command not found")
            if command.status in TERMINAL_COMMAND_STATUSES:
                raise WorkflowConflictError("A terminal command cannot be planned")
            if len(command.input) > self.settings.supervisor_max_command_chars:
                raise WorkflowConflictError("Command exceeds the configured AI input limit")
            if self.runs.has_active_for_command(command_id):
                raise WorkflowConflictError("Supervisor planning is already in progress")

            current_plan = self.plans.get_current_for_command_for_update(command_id, user_id)
            previous_summary = None
            if regenerate:
                if current_plan is None or current_plan.status != PlanStatus.DRAFT:
                    raise WorkflowConflictError("Only a current draft plan can be regenerated")
                previous_summary = self._plan_summary(current_plan, user_id)
                self._cancel_plan(current_plan, user_id, feedback or "Changes requested")
            elif current_plan is not None:
                raise WorkflowConflictError("Command already has a current plan")

            agent_models = self.agents.list_active()
            if not agent_models:
                raise SupervisorPlanningError("No active agents are available")
            agents = [
                AvailableAgent(
                    id=agent.id,
                    name=agent.name,
                    description=agent.description,
                )
                for agent in agent_models
            ]
            command_input = command.input
            run = SupervisorRun(
                command_id=command.id,
                user_id=user_id,
                status=SupervisorRunStatus.RUNNING,
                provider=self.provider.provider_name,
                model=self.provider.model_name,
                prompt_version=PROMPT_VERSION,
                user_feedback=feedback,
            )
            self.runs.add(run)
            command.status = CommandStatus.PLANNING
            self.session.flush()
            run_id = run.id
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        logger.info(
            "supervisor_run_started",
            extra={
                "run_id": str(run_id),
                "command_id": str(command_id),
                "provider": self.provider.provider_name,
                "model": self.provider.model_name,
            },
        )
        return PlanningContext(
            run_id=run_id,
            command_input=command_input,
            agents=agents,
            previous_plan_summary=previous_summary,
            feedback=feedback,
        )

    def _call_and_persist(
        self,
        context: PlanningContext,
        command_id: UUID,
        user_id: UUID,
    ) -> SupervisorPlanningResult:
        try:
            result = self.provider.generate_structured(
                system_prompt=build_system_prompt(
                    context.agents,
                    self.settings.supervisor_max_tasks,
                ),
                user_prompt=build_user_prompt(
                    context.command_input,
                    feedback=context.feedback,
                    previous_plan_summary=context.previous_plan_summary,
                ),
                response_model=SupervisorPlanProposal,
            )
            proposal = self._validate_proposal(result.data, context.agents)
            return self._persist_result(context.run_id, command_id, user_id, proposal, result)
        except (AIError, WorkflowConflictError, SupervisorPlanningError) as error:
            self._mark_failed(context.run_id, command_id, user_id, error)
            raise
        except Exception as error:
            wrapped = SupervisorPlanningError("Supervisor planning failed")
            self._mark_failed(context.run_id, command_id, user_id, wrapped)
            raise wrapped from error

    def _validate_proposal(
        self,
        proposal: SupervisorPlanProposal,
        agents: list[AvailableAgent],
    ) -> SupervisorPlanProposal:
        if len(proposal.tasks) > self.settings.supervisor_max_tasks:
            raise AIInvalidResponseError("Supervisor returned too many tasks")
        active_ids = {agent.id for agent in agents}
        unknown_ids = {task.agent_id for task in proposal.tasks} - active_ids
        if unknown_ids:
            raise AIInvalidResponseError("Supervisor referenced an unavailable agent")
        proposal = self.risk_policy.enforce(proposal)
        self.assignment_policy.validate(proposal)
        return proposal.model_copy(
            update={"tasks": sorted(proposal.tasks, key=lambda task: task.sequence)}
        )

    def _persist_result(
        self,
        run_id: UUID,
        command_id: UUID,
        user_id: UUID,
        proposal: SupervisorPlanProposal,
        result: LLMResult[SupervisorPlanProposal],
    ) -> SupervisorPlanningResult:
        try:
            command = self.commands.get_owned_for_update(command_id, user_id)
            run = self.runs.get_owned_for_update(run_id, user_id)
            if command is None or run is None:
                raise WorkflowNotFoundError("Supervisor run not found")
            if command.status == CommandStatus.CANCELLED:
                run.status = SupervisorRunStatus.CANCELLED
                run.error_code = "command_cancelled"
                run.error_message = "Command was cancelled during planning"
                run.completed_at = utc_now()
                self.session.commit()
                raise WorkflowConflictError("Command was cancelled during planning")
            if command.status in TERMINAL_COMMAND_STATUSES:
                raise WorkflowConflictError("Command can no longer receive a plan")
            if self.plans.get_current_for_command_for_update(command_id, user_id) is not None:
                raise WorkflowConflictError("Command already has a current plan")

            plan = Plan(
                command_id=command_id,
                version=self.plans.next_version(command_id),
                is_current=True,
                title=proposal.title,
                objective=proposal.objective,
                reasoning_summary=proposal.reasoning_summary,
                status=PlanStatus.DRAFT,
            )
            self.plans.add(plan)
            self.session.flush()
            tasks = [
                Task(
                    plan_id=plan.id,
                    agent_id=item.agent_id,
                    title=item.title,
                    instructions=item.instructions,
                    priority=item.priority,
                    risk_level=item.risk_level,
                    sequence=item.sequence,
                    status=TaskStatus.PENDING,
                )
                for item in proposal.tasks
            ]
            self.tasks.add_all(tasks)
            self.session.flush()
            for task in tasks:
                self.history.add(
                    TaskStatusHistory(
                        task_id=task.id,
                        from_status=None,
                        to_status=TaskStatus.PENDING,
                        changed_by_user_id=user_id,
                    )
                )
            self._complete_run(run, result)
            command.status = CommandStatus.PLANNING
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise WorkflowConflictError("A plan was created concurrently") from error
        except Exception:
            self.session.rollback()
            raise

        logger.info(
            "supervisor_run_completed",
            extra=self._log_metadata(run, command_id),
        )
        return SupervisorPlanningResult(plan=plan, tasks=tasks, run=run)

    def _complete_run(
        self,
        run: SupervisorRun,
        result: LLMResult[SupervisorPlanProposal],
    ) -> None:
        run.status = SupervisorRunStatus.COMPLETED
        run.provider = result.provider
        run.model = result.model
        run.input_tokens = result.input_tokens
        run.output_tokens = result.output_tokens
        run.total_tokens = result.total_tokens
        run.estimated_cost = result.estimated_cost
        run.currency = result.currency
        run.latency_ms = result.latency_ms
        run.request_id = result.request_id
        run.completed_at = utc_now()

    def _mark_failed(
        self,
        run_id: UUID,
        command_id: UUID,
        user_id: UUID,
        error: Exception,
    ) -> None:
        self.session.rollback()
        try:
            command = self.commands.get_owned_for_update(command_id, user_id)
            run = self.runs.get_owned_for_update(run_id, user_id)
            if run is None:
                return
            if run.status != SupervisorRunStatus.CANCELLED:
                run.status = SupervisorRunStatus.FAILED
                run.error_code = type(error).__name__
                run.error_message = self._safe_error_message(error)
                run.completed_at = utc_now()
            if (
                command is not None
                and command.status != CommandStatus.CANCELLED
                and self.plans.get_current_for_command_for_update(command_id, user_id) is None
            ):
                command.status = CommandStatus.PENDING
            self.session.commit()
            logger.info(
                "supervisor_run_failed",
                extra=self._log_metadata(run, command_id),
            )
        except Exception:
            self.session.rollback()
            logger.error(
                "supervisor_run_failure_persistence_failed",
                extra={"run_id": str(run_id), "command_id": str(command_id)},
            )

    def _cancel_plan(self, plan: Plan, user_id: UUID, reason: str) -> None:
        now = utc_now()
        plan.status = PlanStatus.CANCELLED
        plan.is_current = False
        plan.rejection_reason = reason
        for task in self.tasks.list_for_plan_owned_for_update(plan.id, user_id):
            if task.status in {TaskStatus.PENDING, TaskStatus.READY}:
                previous = task.status
                task.status = TaskStatus.CANCELLED
                task.completed_at = now
                self.history.add(
                    TaskStatusHistory(
                        task_id=task.id,
                        from_status=previous,
                        to_status=TaskStatus.CANCELLED,
                        changed_by_user_id=user_id,
                        reason=reason,
                    )
                )

    def _plan_summary(self, plan: Plan, user_id: UUID) -> str:
        tasks = self.tasks.list_for_plan_owned(plan.id, user_id)
        task_lines = "; ".join(
            f"{task.sequence}. {task.agent_id}: {task.title}" for task in tasks[:20]
        )
        return (
            f"Plan v{plan.version}: {plan.title}. Objective: {plan.objective}. Tasks: {task_lines}"
        )

    @staticmethod
    def _safe_error_message(error: Exception) -> str:
        if isinstance(error, AIError):
            return str(error)[:500]
        if isinstance(error, WorkflowConflictError):
            return str(error)[:500]
        return "Supervisor planning failed"

    @staticmethod
    def _log_metadata(run: SupervisorRun, command_id: UUID) -> dict[str, object]:
        return {
            "run_id": str(run.id),
            "correlation_id": str(run.correlation_id),
            "command_id": str(command_id),
            "provider": run.provider,
            "model": run.model,
            "latency": run.latency_ms,
            "tokens": run.total_tokens,
            "error_code": run.error_code,
        }
