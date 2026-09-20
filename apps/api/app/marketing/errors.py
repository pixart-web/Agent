from app.execution.exceptions import ExecutionError, ToolInputValidationError


class MarketingError(ExecutionError):
    code = "marketing_error"


class MarketingNotFoundError(MarketingError):
    code = "marketing_not_found"


class MarketingConflictError(MarketingError):
    code = "marketing_conflict"


class MarketingValidationError(ToolInputValidationError, MarketingError):
    code = "marketing_validation_error"
