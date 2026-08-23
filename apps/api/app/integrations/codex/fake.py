from app.execution.context import ExecutionContext
from app.integrations.codex.schemas import CodexTaskRequest, CodexTaskResult


class FakeCodexRunner:
    def __init__(
        self,
        result: CodexTaskResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[CodexTaskRequest, ExecutionContext]] = []

    def run_task(
        self,
        request: CodexTaskRequest,
        context: ExecutionContext,
    ) -> CodexTaskResult:
        self.calls.append((request, context))
        if self.error is not None:
            raise self.error
        if self.result is not None:
            return self.result
        if request.mode == "review":
            return CodexTaskResult(
                summary="Fake Codex review completed",
                findings=[],
                risk="low",
                recommended_action="No action required",
                pull_request_number=request.pull_request_number,
                exit_code=0,
                model="fake-codex",
            )
        return CodexTaskResult(
            summary="Fake Codex implementation completed",
            files_changed=["README.md"],
            tests_run=["pnpm test"],
            tests_passed=True,
            commit_sha="a" * 40,
            branch=request.working_branch,
            pull_request_number=request.pull_request_number,
            exit_code=0,
            model="fake-codex",
        )
