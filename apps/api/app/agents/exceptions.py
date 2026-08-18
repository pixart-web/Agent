class SpecializedAgentError(Exception):
    pass


class AgentNotRegisteredError(SpecializedAgentError):
    pass


class AgentProposalError(SpecializedAgentError):
    pass
