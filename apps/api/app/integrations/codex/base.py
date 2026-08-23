from typing import Protocol

from app.execution.context import ExecutionContext
from app.integrations.codex.schemas import CodexTaskRequest, CodexTaskResult


class CodexRunner(Protocol):
    def run_task(
        self,
        request: CodexTaskRequest,
        context: ExecutionContext,
    ) -> CodexTaskResult: ...
