from app.execution.registry import ToolDefinition, ToolRegistry
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
from app.models.workflow_enums import RiskLevel

ALL_AGENTS = frozenset({"supervisor", "marketing", "sales", "support", "development"})


def build_tool_registry() -> ToolRegistry:
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
    return registry
