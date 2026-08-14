from app.ai.exceptions import AIInvalidResponseError
from app.schemas.supervisor import SupervisorPlanProposal


class AgentAssignmentPolicy:
    CRITICAL_RULES = (
        (
            ("deploy to production", "production deploy", "delete database"),
            {"development", "supervisor"},
        ),
        (("sign contract", "transfer money", "make payment"), {"supervisor"}),
        (("resolve customer incident", "customer support ticket"), {"support", "supervisor"}),
    )

    def validate(self, proposal: SupervisorPlanProposal) -> None:
        for task in proposal.tasks:
            content = f"{task.title} {task.instructions}".lower()
            for terms, allowed_agents in self.CRITICAL_RULES:
                if any(term in content for term in terms) and task.agent_id not in allowed_agents:
                    raise AIInvalidResponseError(
                        f"Task {task.sequence} has an invalid critical agent assignment"
                    )
