from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from app.execution.context import ExecutionContext
from app.execution.exceptions import (
    ToolInputValidationError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolVersionError,
)
from app.models.workflow_enums import RiskLevel


class ToolHandler(Protocol):
    def execute(self, context: ExecutionContext, payload: BaseModel) -> BaseModel: ...


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    version: str
    description: str
    agent_types: frozenset[str]
    risk_level: RiskLevel
    timeout_seconds: int
    max_retries: int
    requires_approval: bool
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[tuple[str, str], ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        key = (definition.name, definition.version)
        if key in self._tools:
            raise ValueError(f"Tool already registered: {definition.name}@{definition.version}")
        self._tools[key] = definition

    def get(self, name: str, version: str) -> ToolDefinition:
        definition = self._tools.get((name, version))
        if definition is not None:
            return definition
        if any(tool_name == name for tool_name, _ in self._tools):
            raise ToolVersionError(f"Unsupported tool version: {name}@{version}")
        raise ToolNotFoundError(f"Tool is not registered: {name}")

    def validate_input(
        self,
        definition: ToolDefinition,
        payload: dict[str, object],
        agent_id: str,
    ) -> BaseModel:
        if agent_id not in definition.agent_types and "*" not in definition.agent_types:
            raise ToolPermissionError("Agent is not allowed to use this tool")
        try:
            return definition.input_schema.model_validate(payload)
        except Exception as error:
            raise ToolInputValidationError("Tool input does not match its schema") from error

    def definitions(self) -> list[ToolDefinition]:
        return list(self._tools.values())
