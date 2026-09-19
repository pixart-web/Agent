from app.execution.exceptions import ExecutionError, ToolInputValidationError


class CrmError(ExecutionError):
    code = "crm_error"


class CrmNotFoundError(CrmError):
    code = "crm_not_found"


class CrmConflictError(CrmError):
    code = "crm_conflict"


class CrmValidationError(ToolInputValidationError, CrmError):
    code = "crm_validation_error"
