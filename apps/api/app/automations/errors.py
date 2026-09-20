class AutomationError(Exception):
    pass


class AutomationNotFoundError(AutomationError):
    pass


class AutomationConflictError(AutomationError):
    pass


class AutomationValidationError(AutomationError):
    pass
