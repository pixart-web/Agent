from app.models.workflow_enums import RiskLevel
from app.schemas.supervisor import SupervisorPlanProposal


class RiskPolicy:
    RED_TERMS = (
        "delete data",
        "erase data",
        "payment",
        "transfer money",
        "production deploy",
        "deploy to production",
        "sign contract",
        "accept contract",
        "credential",
        "api key",
    )
    YELLOW_TERMS = (
        "send email",
        "publish",
        "post on",
        "alter website",
        "change website",
        "launch campaign",
        "create campaign",
    )

    def enforce(self, proposal: SupervisorPlanProposal) -> SupervisorPlanProposal:
        tasks = []
        for task in proposal.tasks:
            content = f"{task.title} {task.instructions}".lower()
            minimum = self._minimum_risk(content)
            risk = task.risk_level
            if minimum == RiskLevel.RED:
                risk = RiskLevel.RED
            elif minimum == RiskLevel.YELLOW and risk == RiskLevel.GREEN:
                risk = RiskLevel.YELLOW
            tasks.append(task.model_copy(update={"risk_level": risk}))
        return proposal.model_copy(update={"tasks": tasks})

    def _minimum_risk(self, content: str) -> RiskLevel:
        if any(term in content for term in self.RED_TERMS):
            return RiskLevel.RED
        if any(term in content for term in self.YELLOW_TERMS):
            return RiskLevel.YELLOW
        return RiskLevel.GREEN
