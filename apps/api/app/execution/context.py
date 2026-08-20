from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ExecutionContext:
    user_id: UUID
    command_id: UUID
    task_id: UUID
    action_id: UUID
    execution_id: UUID
    correlation_id: UUID
