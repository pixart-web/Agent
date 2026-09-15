from app.execution.exceptions import (
    ExecutionError,
    ToolInputValidationError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolTransientError,
)


class EmailError(ExecutionError):
    code = "email_error"


class EmailAuthenticationError(EmailError):
    code = "email_authentication_error"


class EmailPermissionError(ToolPermissionError, EmailError):
    code = "email_permission_error"


class EmailNotFoundError(EmailError):
    code = "email_not_found"


class EmailValidationError(ToolInputValidationError, EmailError):
    code = "email_validation_error"


class EmailRateLimitError(ToolTransientError, EmailError):
    code = "email_rate_limited"


class EmailTimeoutError(ToolTimeoutError, EmailError):
    code = "email_timeout"


class EmailTransientError(ToolTransientError, EmailError):
    code = "email_transient_error"


class EmailDeliveryUnknownError(EmailError):
    code = "email_delivery_unknown"
