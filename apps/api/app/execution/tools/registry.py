from app.core.config import Settings
from app.execution.registry import ToolDefinition, ToolRegistry
from app.execution.tools.codex import codex_tool_definitions
from app.execution.tools.email import email_tool_definitions
from app.execution.tools.github import github_tool_definitions
from app.execution.tools.internal import (
    CreateNoteHandler,
    CreateNoteInput,
    CreateNoteOutput,
    EchoHandler,
    EchoInput,
    EchoOutput,
    SimulatedActionHandler,
    SimulatedActionInput,
    SimulatedActionOutput,
    SummarizeHandler,
    SummarizeInput,
    SummarizeOutput,
)
from app.integrations.codex.base import CodexRunner
from app.integrations.email.service import EmailService
from app.integrations.github.client import GitHubClientFactory, build_github_client
from app.models.workflow_enums import RiskLevel

ALL_AGENTS = frozenset({"supervisor", "marketing", "sales", "support", "development"})


def build_tool_registry(
    *,
    settings: Settings | None = None,
    github_client_factory: GitHubClientFactory = build_github_client,
    codex_runner: CodexRunner | None = None,
    email_service: EmailService | None = None,
) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="internal.echo",
            version="1",
            description="Return supplied text unchanged.",
            agent_types=ALL_AGENTS,
            risk_level=RiskLevel.GREEN,
            timeout_seconds=10,
            max_retries=0,
            requires_approval=False,
            input_schema=EchoInput,
            output_schema=EchoOutput,
            handler=EchoHandler(),
        )
    )
    registry.register(
        ToolDefinition(
            name="internal.summarize",
            version="1",
            description="Create a structured summary through the configured AI provider.",
            agent_types=ALL_AGENTS,
            risk_level=RiskLevel.GREEN,
            timeout_seconds=60,
            max_retries=2,
            requires_approval=False,
            input_schema=SummarizeInput,
            output_schema=SummarizeOutput,
            handler=SummarizeHandler(),
        )
    )
    registry.register(
        ToolDefinition(
            name="internal.create_note",
            version="1",
            description="Store an internal note as the execution result linked to the task.",
            agent_types=ALL_AGENTS,
            risk_level=RiskLevel.GREEN,
            timeout_seconds=10,
            max_retries=0,
            requires_approval=False,
            input_schema=CreateNoteInput,
            output_schema=CreateNoteOutput,
            handler=CreateNoteHandler(),
        )
    )
    registry.register(
        ToolDefinition(
            name="internal.simulate_external_action",
            version="1",
            description="Simulate an external action without contacting any service.",
            agent_types=ALL_AGENTS,
            risk_level=RiskLevel.YELLOW,
            timeout_seconds=10,
            max_retries=0,
            requires_approval=True,
            input_schema=SimulatedActionInput,
            output_schema=SimulatedActionOutput,
            handler=SimulatedActionHandler(),
        )
    )
    registry.register(
        ToolDefinition(
            name="internal.simulate_critical_action",
            version="1",
            description="Simulate a critical action without external effects.",
            agent_types=frozenset({"supervisor", "development"}),
            risk_level=RiskLevel.RED,
            timeout_seconds=10,
            max_retries=0,
            requires_approval=True,
            input_schema=SimulatedActionInput,
            output_schema=SimulatedActionOutput,
            handler=SimulatedActionHandler(),
        )
    )
    for definition in codex_tool_definitions(settings=settings, runner=codex_runner):
        registry.register(definition)
    for definition in email_tool_definitions(settings=settings, service=email_service):
        registry.register(definition)
    for definition in github_tool_definitions(
        settings=settings, client_factory=github_client_factory
    ):
        registry.register(definition)
    return registry
