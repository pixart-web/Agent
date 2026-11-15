"""Tool-constrained response models for specialist agents.

Local models follow a JSON Schema far more reliably than prose instructions. Instead of the
generic `AgentProposal` (whose `input_payload` is a free-form object), the runner asks the
model for a proposal whose actions are a discriminated union with one variant per allowed tool:
`tool_name` and `tool_version` are constants and `input_payload` is that tool's real input
schema. A runtime that enforces schemas (Ollama `format`) then cannot produce unknown tools,
invented versions or missing/ill-typed arguments. The result is converted back to the generic
`AgentProposal`, and the runner still validates every action against the tool registry.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, create_model

from app.execution.registry import ToolDefinition
from app.models.workflow_enums import RiskLevel
from app.schemas.specialized_agent import AgentActionProposal, AgentProposal


def _variant(definition: ToolDefinition) -> type[BaseModel]:
    safe = "".join(ch if ch.isalnum() else "_" for ch in definition.name)
    return create_model(
        f"Action_{safe}_v{definition.version}",
        tool_name=(Literal[definition.name], ...),  # type: ignore[valid-type]
        tool_version=(Literal[definition.version], definition.version),  # type: ignore[valid-type]
        input_payload=(definition.input_schema, ...),
        reason=(str, Field(min_length=1, max_length=2000)),
        expected_outcome=(str, Field(min_length=1, max_length=2000)),
        risk_level=(RiskLevel, RiskLevel.GREEN),
        sequence=(int, Field(ge=1)),
    )


@lru_cache(maxsize=64)
def _proposal_model(definitions: tuple[ToolDefinition, ...]) -> type[BaseModel]:
    variants = tuple(_variant(item) for item in definitions)
    action = (
        variants[0]
        if len(variants) == 1
        else Annotated[Union[variants], Field(discriminator="tool_name")]  # noqa: UP007
    )
    return create_model(
        "ConstrainedAgentProposal",
        summary=(str, Field(min_length=1, max_length=5000)),
        actions=(list[action], Field(min_length=1)),  # type: ignore[valid-type]
    )


def proposal_model_for(definitions: list[ToolDefinition]) -> type[BaseModel]:
    """Response model restricted to the given tools (stable order, cached)."""
    ordered = tuple(sorted(definitions, key=lambda item: (item.name, item.version)))
    return _proposal_model(ordered)


def _payload(value: object) -> dict[str, object]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    return dict(value)  # already a plain mapping (e.g. a generic AgentProposal)


def to_agent_proposal(value: BaseModel) -> AgentProposal:
    if isinstance(value, AgentProposal):
        return value
    actions = [
        AgentActionProposal(
            tool_name=item.tool_name,
            tool_version=item.tool_version,
            input_payload=_payload(item.input_payload),
            reason=item.reason,
            expected_outcome=item.expected_outcome,
            risk_level=item.risk_level,
            sequence=item.sequence,
        )
        for item in value.actions
    ]
    return AgentProposal(summary=value.summary, actions=actions)
