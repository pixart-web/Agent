from dataclasses import dataclass

from app.ai.exceptions import AIInvalidResponseError
from app.models.workflow_enums import RiskLevel, TaskPriority
from app.schemas.supervisor import SupervisorPlanProposal, SupervisorTaskProposal
from app.services.agent_assignment_policy import AgentAssignmentPolicy
from app.services.risk_policy import RiskPolicy


@dataclass(frozen=True)
class PolicyCase:
    name: str
    agent_id: str
    instructions: str
    expected_risk: RiskLevel
    assignment_allowed: bool


CASES = (
    PolicyCase(
        "safe summary", "marketing", "Summarize approved campaign facts", RiskLevel.GREEN, True
    ),
    PolicyCase("email write", "support", "Send email to the customer", RiskLevel.YELLOW, True),
    PolicyCase("production deploy", "development", "Deploy to production", RiskLevel.RED, True),
    PolicyCase("wrong deploy agent", "marketing", "Deploy to production", RiskLevel.RED, False),
    PolicyCase(
        "financial authority", "sales", "Transfer money to a supplier", RiskLevel.RED, False
    ),
    PolicyCase("support routing", "support", "Resolve customer incident", RiskLevel.GREEN, True),
)


def evaluate_policy_suite() -> dict[str, object]:
    results = []
    risk_policy = RiskPolicy()
    assignment_policy = AgentAssignmentPolicy()
    for case in CASES:
        proposal = SupervisorPlanProposal(
            title=f"Evaluation: {case.name}",
            objective="Validate deterministic safety policy",
            tasks=[
                SupervisorTaskProposal(
                    agent_id=case.agent_id,
                    title=case.name,
                    instructions=case.instructions,
                    priority=TaskPriority.NORMAL,
                    risk_level=RiskLevel.GREEN,
                    sequence=1,
                )
            ],
        )
        enforced = risk_policy.enforce(proposal)
        assignment_allowed = True
        try:
            assignment_policy.validate(enforced)
        except AIInvalidResponseError:
            assignment_allowed = False
        passed = (
            enforced.tasks[0].risk_level == case.expected_risk
            and assignment_allowed == case.assignment_allowed
        )
        results.append(
            {
                "name": case.name,
                "passed": passed,
                "risk": enforced.tasks[0].risk_level.value,
                "assignment_allowed": assignment_allowed,
            }
        )
    passed_count = sum(1 for result in results if result["passed"])
    return {
        "suite": "policy_quality_v1",
        "passed": passed_count,
        "total": len(results),
        "pass_rate": passed_count / len(results),
        "results": results,
    }
