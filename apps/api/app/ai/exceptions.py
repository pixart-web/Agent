class AIError(Exception):
    """Base error safe for domain mapping."""


class AIConfigurationError(AIError):
    pass


class AIProviderUnavailableError(AIError):
    pass


class AIProviderTimeoutError(AIError):
    pass


class AIInvalidResponseError(AIError):
    pass


class SupervisorPlanningError(AIError):
    pass
