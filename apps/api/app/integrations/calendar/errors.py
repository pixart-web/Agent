from app.execution.exceptions import (
    ExecutionError,
    ToolInputValidationError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolTransientError,
)


class CalendarError(ExecutionError):
    code = "calendar_error"


class CalendarAuthenticationError(CalendarError):
    code = "calendar_authentication_error"


class CalendarPermissionError(ToolPermissionError, CalendarError):
    code = "calendar_permission_error"


class CalendarNotFoundError(CalendarError):
    code = "calendar_not_found"


class CalendarValidationError(ToolInputValidationError, CalendarError):
    code = "calendar_validation_error"


class CalendarRateLimitError(ToolTransientError, CalendarError):
    code = "calendar_rate_limited"


class CalendarTimeoutError(ToolTimeoutError, CalendarError):
    code = "calendar_timeout"


class CalendarTransientError(ToolTransientError, CalendarError):
    code = "calendar_transient_error"


class CalendarDeliveryUnknownError(CalendarError):
    code = "calendar_delivery_unknown"
