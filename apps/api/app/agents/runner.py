import json
import logging
import re
from dataclasses import asdict, dataclass, fields, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents.constrained import proposal_model_for
from app.agents.context import AgentContextBuilder, AgentTaskContext
from app.agents.exceptions import AgentProposalError
from app.agents.registry import SpecializedAgentRegistry, build_agent_registry
from app.ai.base import LLMProvider, LLMResult
from app.ai.exceptions import AIError
from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.execution.context import ExecutionContext
from app.execution.context_safety import sanitize_execution_payload
from app.execution.exceptions import ToolInputValidationError
from app.execution.policies import ExecutionRiskPolicy, action_fingerprint, maximum_risk
from app.execution.registry import ToolRegistry
from app.execution.tools.registry import build_tool_registry
from app.integrations.credentials import EnvironmentCredentialProvider
from app.models.agent_configuration import AgentConfiguration
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
    RiskLevel,
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
from app.workspaces.scope import active_workspace_id

logger = logging.getLogger(__name__)
MAX_TOOL_SCHEMA_CHARS = 600
STALE_RUN_MARGIN_SECONDS = 120
# Read-only internal tools an agent may run before proposing actions (the lookup round).
LOOKUP_NAMESPACES = ("crm.", "marketing.", "knowledge.")
LOOKUP_OPERATIONS = ("list_", "search", "get_")
MAX_LOOKUPS = 3
LOOKUP_RESULT_CHARS = 1_500
_UUID_FIELDS = {"user_id", "command_id", "correlation_id", "task_id"}


def context_to_payload(context: AgentTaskContext) -> dict[str, object]:
    """JSON-safe form of an agent context, for the background worker."""
    payload = asdict(context)
    for name in _UUID_FIELDS:
        payload[name] = str(payload[name])
    for name, value in payload.items():
        if isinstance(value, tuple):
            payload[name] = list(value)
    return payload


def context_from_payload(payload: dict[str, object]) -> AgentTaskContext:
    values: dict[str, object] = {}
    for item in fields(AgentTaskContext):
        if item.name not in payload:
            continue
        value = payload[item.name]
        if item.name in _UUID_FIELDS:
            value = UUID(str(value))
        elif isinstance(value, list):
            value = tuple(value)
        values[item.name] = value
    return AgentTaskContext(**values)  # type: ignore[arg-type]


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

    def start(
        self, task_id: UUID, user_id: UUID, feedback: str | None = None
    ) -> tuple[AgentTaskContext, UUID]:
        """Open an agent run without calling the model; `complete` finishes it later.

        Used for background runs: the API answers at once and a worker runs the model. A task
        that already has runs is re-run (keeping the history), which needs a failed run,
        reset actions or feedback.
        """
        if feedback and len(feedback) > self.settings.agent_max_feedback_chars:
            raise WorkflowConflictError("Feedback exceeds the configured limit")
        rerun = bool(self.runs.list_for_task_owned(task_id, user_id))
        self.session.rollback()
        return self._start(task_id, user_id, feedback=feedback, rerun=rerun)

    def complete(
        self, context: AgentTaskContext, run_id: UUID, user_id: UUID
    ) -> AgentRunnerResult | None:
        """Run the model for a started run. Returns None when the run is no longer running
        (a redelivered task, or a run cancelled or failed meanwhile)."""
        run = self.runs.get_owned_for_update(run_id, user_id)
        still_running = run is not None and run.status == AgentRunStatus.RUNNING
        self.session.rollback()  # release the row lock before the (long) model call
        if not still_running:
            return None
        return self._call_and_persist(context, run_id, user_id)

    def fail(self, run_id: UUID, user_id: UUID, error: Exception) -> None:
        self._mark_failed(run_id, user_id, error)

    def stale_cutoff(self) -> datetime:
        """Runs still active after the longest possible model work are abandoned. An agent
        run may call the model three times (proposal, one repair, one lookup round)."""
        budget = 3 * self.settings.ai_request_timeout_seconds * (self.settings.ai_max_retries + 1)
        return utc_now() - timedelta(seconds=budget + STALE_RUN_MARGIN_SECONDS)

    def _start(
        self, task_id: UUID, user_id: UUID, *, feedback: str | None, rerun: bool
    ) -> tuple[AgentTaskContext, UUID]:
        try:
            task = self.tasks.get_owned_for_update(task_id, user_id)
            if task is None:
                raise WorkflowNotFoundError("Task not found")
            if self.runs.fail_stale_for_task(task.id, self.stale_cutoff()):
                self.session.flush()
                rerun = True
            if task.status != TaskStatus.READY:
                raise WorkflowConflictError("Only a ready task can run its assigned agent")
            if not self.dependencies.satisfied(task.id):
                raise WorkflowConflictError("Task dependencies are not completed")
            plan = self.session.get(Plan, task.plan_id)
            command = self.session.scalar(
                select(Command)
                .where(
                    Command.id == plan.command_id,
                    Command.workspace_id == active_workspace_id(user_id),
                )
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
            configuration = self.session.scalar(
                select(AgentConfiguration).where(
                    AgentConfiguration.workspace_id == command.workspace_id,
                    AgentConfiguration.agent_id == task.agent_id,
                )
            )
            if configuration is not None and not configuration.enabled:
                raise WorkflowConflictError("Assigned agent is disabled for this workspace")
            if (
                configuration is not None
                and configuration.model is not None
                and configuration.model != self.provider.model_name
            ):
                raise WorkflowConflictError("Configured agent model is unavailable")
            if configuration is not None and configuration.monthly_token_budget is not None:
                month_start = datetime.now(UTC).replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                tokens_used = self.session.scalar(
                    select(func.coalesce(func.sum(AgentRun.total_tokens), 0))
                    .join(Task, Task.id == AgentRun.task_id)
                    .join(Plan, Plan.id == Task.plan_id)
                    .join(Command, Command.id == Plan.command_id)
                    .where(
                        AgentRun.agent_id == task.agent_id,
                        AgentRun.created_at >= month_start,
                        Command.workspace_id == command.workspace_id,
                    )
                )
                if tokens_used >= configuration.monthly_token_budget:
                    raise WorkflowConflictError("Agent monthly token budget is exhausted")
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
            allowed_tools = agent.allowed_tools
            if configuration is not None and configuration.allowed_tools is not None:
                allowed_tools = allowed_tools.intersection(configuration.allowed_tools)
            context = self.context_builder.build(
                task,
                user_id,
                allowed_tools,
                feedback,
                self.settings.agent_max_context_chars,
            )
            context = replace(context, tool_specs=self._tool_specs(allowed_tools))
            usable = {item.name for item in self._usable_definitions(context)}
            context = replace(
                context,
                tool_specs=tuple(
                    spec for spec in context.tool_specs if spec[2:].split("@", 1)[0] in usable
                ),
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
        response_model = self._constrained_model(context)
        try:
            result = agent.propose_actions(
                context=context, provider=self.provider, response_model=response_model
            )
            try:
                proposal = self._validate(result.data, context, agent)
            except (ToolInputValidationError, AgentProposalError) as rejected:
                # One repair round: tell the model exactly why the proposal was rejected.
                # Validation itself is never relaxed.
                retry_context = replace(
                    context,
                    feedback=(
                        f"{context.feedback + chr(10) if context.feedback else ''}"
                        f"Your previous proposal was rejected: {self._rejection(rejected)}. "
                        "Use only the listed tools and make every input_payload match the "
                        "tool input schema exactly."
                    ),
                )
                result = agent.propose_actions(
                    context=retry_context, provider=self.provider, response_model=response_model
                )
                proposal = self._validate(result.data, retry_context, agent)
            proposal, result = self._lookup_round(context, run_id, agent, proposal, result)
            return self._persist(run_id, user_id, proposal, result)
        except Exception as error:
            self._mark_failed(run_id, user_id, error)
            if isinstance(error, (AIError, WorkflowConflictError, AgentProposalError)):
                raise
            raise AgentProposalError("Specialized agent proposal failed validation") from error

    def _lookup_round(self, context: AgentTaskContext, run_id: UUID, agent, proposal, result):
        """When the task names no records and the agent only proposed read-only lookups, run
        them now and ask the agent once more, with the results, for the actions that complete
        the task. The lookups never change data; the final proposal is validated as usual.
        If the second answer is unusable, the lookup proposal is kept (nothing is lost)."""
        if not self.settings.agent_lookup_round_enabled or not proposal.actions:
            return proposal, result
        if self._known_identifier(context):
            return proposal, result
        definitions = [self.tools.get(a.tool_name, a.tool_version) for a in proposal.actions]
        if not all(is_lookup_tool(definition) for definition in definitions):
            return proposal, result
        findings = []
        for item, definition in list(zip(proposal.actions, definitions, strict=True))[:MAX_LOOKUPS]:
            findings.append(self._run_lookup(context, agent.agent_id, item, definition))
        self.audit.record(
            actor_type=ActorType.AGENT,
            actor_id=None,
            event_type="agent_lookup_performed",
            resource_type="agent_run",
            resource_id=run_id,
            metadata={
                "task_id": str(context.task_id),
                "tools": [item.tool_name for item in proposal.actions[:MAX_LOOKUPS]],
            },
            correlation_id=context.correlation_id,
        )
        self.session.commit()
        lookup_context = replace(
            context,
            feedback=(
                f"{context.feedback + chr(10) if context.feedback else ''}"
                "Read-only lookups already done (do not repeat them):\n"
                + "\n".join(findings)
                + "\nNow propose the actions that complete the task, using the real "
                "identifiers above. If nothing found fits, propose an internal note "
                "explaining what is missing."
            ),
        )
        try:
            second = agent.propose_actions(
                context=lookup_context,
                provider=self.provider,
                response_model=self._constrained_model(lookup_context),
            )
            return self._validate(second.data, lookup_context, agent), second
        except (ToolInputValidationError, AgentProposalError) as rejected:
            logger.info(
                "agent_lookup_round_rejected",
                extra={"agent_run_id": str(run_id), "reason": self._rejection(rejected)},
            )
            return proposal, result

    def _run_lookup(self, context: AgentTaskContext, agent_id: str, item, definition) -> str:
        call = f"- {item.tool_name}({json.dumps(item.input_payload, default=str)[:300]})"
        try:
            payload = self.tools.validate_input(definition, item.input_payload, agent_id)
            output = definition.handler.execute(
                ExecutionContext(
                    user_id=context.user_id,
                    command_id=context.command_id,
                    task_id=context.task_id,
                    action_id=uuid4(),
                    execution_id=uuid4(),
                    correlation_id=context.correlation_id,
                    credentials=EnvironmentCredentialProvider(),
                ),
                payload,
            )
            data = sanitize_execution_payload(
                definition.output_schema.model_validate(output).model_dump(mode="json")
            )
            text = json.dumps(data, ensure_ascii=False, default=str)
            if len(text) > LOOKUP_RESULT_CHARS:
                text = text[:LOOKUP_RESULT_CHARS] + "…(truncated)"
            return f"{call} -> {text}"
        except Exception as error:  # a failed lookup is reported to the model, not raised
            return f"{call} -> failed ({type(error).__name__})"

    @staticmethod
    def _known_identifier(context: AgentTaskContext) -> bool:
        return (
            UUID_PATTERN.search(
                " ".join([context.task_instructions, context.plan_objective, context.command_input])
            )
            is not None
        )

    def _tool_specs(self, allowed_tools: frozenset[str]) -> tuple[str, ...]:
        specs = []
        for definition in sorted(self.tools.definitions(), key=lambda item: item.name):
            if definition.name not in allowed_tools:
                continue
            fields = describe_input_fields(definition.input_schema.model_json_schema())
            specs.append(
                f"- {definition.name}@{definition.version}: input_payload {{{fields}}}"[
                    :MAX_TOOL_SCHEMA_CHARS
                ]
            )
        return tuple(specs)

    def _usable_definitions(self, context: AgentTaskContext):
        """Allowed tools the model can actually call: when the task context contains no real
        identifier, tools that require one are left out, so the model has to start with a
        search/list tool instead of inventing ids."""
        allowed = set(context.available_tools)
        definitions = [item for item in self.tools.definitions() if item.name in allowed]
        known_ids = UUID_PATTERN.search(
            " ".join(
                [
                    context.task_instructions,
                    context.plan_objective,
                    context.command_input,
                    context.feedback or "",
                ]
            )
        )
        if known_ids is None:
            without_ids = [item for item in definitions if not requires_identifier(item)]
            if without_ids:
                return without_ids
        return definitions

    def _constrained_model(self, context: AgentTaskContext):
        definitions = self._usable_definitions(context)
        return proposal_model_for(definitions) if definitions else None

    @staticmethod
    def _rejection(error: Exception) -> str:
        cause = error.__cause__
        detail = str(error)
        if cause is not None:
            detail = f"{detail} ({str(cause)[:600]})"
        return detail[:800]

    def _validate(self, proposal: AgentProposal, context: AgentTaskContext, agent) -> AgentProposal:
        maximum = min(self.settings.agent_max_actions_per_task, agent.max_actions_per_task)
        task = self.session.get(Task, context.task_id)
        plan = self.session.get(Plan, task.plan_id)
        command = self.session.get(Command, plan.command_id)
        configuration = self.session.scalar(
            select(AgentConfiguration).where(
                AgentConfiguration.workspace_id == command.workspace_id,
                AgentConfiguration.agent_id == agent.agent_id,
            )
        )
        if configuration is not None and configuration.max_actions_per_task is not None:
            maximum = min(maximum, configuration.max_actions_per_task)
        if len(proposal.actions) > maximum:
            raise AgentProposalError("Agent proposed too many actions")
        validated = []
        allowed_tools = agent.allowed_tools
        if configuration is not None and configuration.allowed_tools is not None:
            allowed_tools = allowed_tools.intersection(configuration.allowed_tools)
        for item in sorted(proposal.actions, key=lambda action: action.sequence):
            if item.tool_name not in allowed_tools:
                raise AgentProposalError("Agent proposed a tool outside its allowlist")
            definition = self.tools.get(item.tool_name, item.tool_version)
            placeholder = find_placeholder_identifier(item.input_payload)
            if placeholder is not None:
                raise AgentProposalError(
                    f"Agent used a placeholder identifier in {item.tool_name}.{placeholder}; "
                    "find the real record with a search or list tool first"
                )
            payload = self.tools.validate_input(definition, item.input_payload, agent.agent_id)
            risk = maximum_risk(
                task.risk_level,
                item.risk_level,
                definition.risk_level,
                self.risk_policy.evaluate(item.input_payload),
            )
            if configuration is not None and configuration.approval_policy == "always":
                risk = maximum_risk(risk, RiskLevel.RED)
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


def describe_input_fields(schema: dict) -> str:
    """Compact field list for a tool input schema: name:type, `*` = required, enums inline."""
    definitions = schema.get("$defs", {})
    required = set(schema.get("required", []))

    def kind(node: dict) -> str:
        if "$ref" in node:
            target = definitions.get(node["$ref"].split("/")[-1], {})
            if "enum" in target:
                return "|".join(map(str, target["enum"]))
            return "object"
        if "enum" in node:
            return "|".join(map(str, node["enum"]))
        for key in ("anyOf", "oneOf"):
            if key in node:
                options = [kind(item) for item in node[key] if item.get("type") != "null"]
                return "/".join(options) or "null"
        if node.get("type") == "array":
            return f"list[{kind(node.get('items', {}))}]"
        return str(node.get("format") or node.get("type") or "any")

    return ", ".join(
        f"{name}{'*' if name in required else ''}:{kind(node)}"
        for name, node in schema.get("properties", {}).items()
    )


NIL_UUID = "00000000-0000-0000-0000-000000000000"


def find_placeholder_identifier(payload: object, path: str = "") -> str | None:
    """Field path of a nil/placeholder UUID anywhere in a proposed tool payload, if any."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            found = find_placeholder_identifier(value, f"{path}.{key}" if path else str(key))
            if found is not None:
                return found
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found = find_placeholder_identifier(value, f"{path}[{index}]")
            if found is not None:
                return found
    elif isinstance(payload, str) and payload.strip().lower() in {NIL_UUID, "uuid", "<uuid>"}:
        return path or "value"
    return None


UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE
)


def is_lookup_tool(definition) -> bool:
    """Read-only internal data tool (list/search/get on CRM, marketing or knowledge)."""
    namespace, _, operation = definition.name.partition(".")
    return (
        definition.name.startswith(LOOKUP_NAMESPACES)
        and operation.startswith(LOOKUP_OPERATIONS)
        and definition.risk_level == RiskLevel.GREEN
        and not definition.requires_approval
    )


def requires_identifier(definition) -> bool:
    """True when the tool input has a required UUID field (it targets an existing record)."""
    schema = definition.input_schema.model_json_schema()
    properties = schema.get("properties", {})
    for name in schema.get("required", []):
        node = properties.get(name, {})
        options = node.get("anyOf", [node])
        if any(option.get("format") == "uuid" for option in options):
            return True
    return False
