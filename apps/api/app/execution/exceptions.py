class ExecutionError(Exception):
    code = "execution_error"
    retryable = False


class ToolNotFoundError(ExecutionError):
    code = "tool_not_found"


class ToolVersionError(ExecutionError):
    code = "tool_version_mismatch"


class ToolInputValidationError(ExecutionError):
    code = "invalid_tool_input"


class ToolPermissionError(ExecutionError):
    code = "tool_permission_denied"


class ToolTimeoutError(ExecutionError):
    code = "tool_timeout"
    retryable = True


class ToolTransientError(ExecutionError):
    code = "tool_transient_error"
    retryable = True


class ApprovalRequiredError(ExecutionError):
    code = "approval_required"


class ApprovalFingerprintError(ExecutionError):
    code = "approval_fingerprint_changed"


class DependencyBlockedError(ExecutionError):
    code = "task_dependencies_blocked"
