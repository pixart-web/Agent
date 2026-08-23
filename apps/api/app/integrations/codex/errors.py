from app.execution.exceptions import ExecutionError


class CodexError(ExecutionError):
    code = "codex_error"


class CodexDisabledError(CodexError):
    code = "codex_disabled"


class CodexRunnerUnavailableError(CodexError):
    code = "codex_runner_unavailable"
    retryable = True


class CodexTimeoutError(CodexError):
    code = "codex_timeout"


class CodexWorkspaceError(CodexError):
    code = "codex_workspace_error"


class CodexPolicyError(CodexError):
    code = "codex_policy_error"


class CodexValidationError(CodexError):
    code = "codex_validation_error"


class CodexTransientError(CodexError):
    code = "codex_transient_error"
    retryable = True
