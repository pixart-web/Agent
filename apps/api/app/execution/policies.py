import hashlib
import json
import random
from collections.abc import Callable
from dataclasses import dataclass

from app.models.workflow_enums import RiskLevel

RISK_ORDER = {RiskLevel.GREEN: 0, RiskLevel.YELLOW: 1, RiskLevel.RED: 2}


def maximum_risk(*levels: RiskLevel) -> RiskLevel:
    return max(levels, key=RISK_ORDER.__getitem__)


def action_fingerprint(
    tool_name: str,
    tool_version: str,
    input_payload: dict[str, object],
    risk_level: RiskLevel,
) -> str:
    canonical = json.dumps(
        {
            "tool_name": tool_name,
            "tool_version": tool_version,
            "input_payload": input_payload,
            "risk_level": risk_level.value,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    delay_seconds: float


class RetryPolicy:
    def __init__(
        self,
        *,
        system_max_retries: int,
        base_seconds: float = 5,
        jitter_ratio: float = 0.2,
        random_value: Callable[[], float] = random.random,
    ) -> None:
        self.system_max_retries = system_max_retries
        self.base_seconds = base_seconds
        self.jitter_ratio = jitter_ratio
        self.random_value = random_value

    def decide(
        self,
        *,
        attempt_number: int,
        tool_max_retries: int,
        retryable: bool,
    ) -> RetryDecision:
        max_retries = min(tool_max_retries, self.system_max_retries)
        if not retryable or attempt_number > max_retries:
            return RetryDecision(False, 0)
        delay = self.base_seconds * (3 ** (attempt_number - 1))
        jitter = delay * self.jitter_ratio * self.random_value()
        return RetryDecision(True, delay + jitter)


class ExecutionRiskPolicy:
    RED_TERMS = (
        "payment",
        "transfer money",
        "delete data",
        "production deploy",
        "sign contract",
        "credential",
    )
    YELLOW_TERMS = (
        "publish",
        "send email",
        "external",
        "update website",
        "launch campaign",
    )

    def evaluate(self, payload: dict[str, object]) -> RiskLevel:
        content = json.dumps(payload, ensure_ascii=False).lower()
        if any(term in content for term in self.RED_TERMS):
            return RiskLevel.RED
        if any(term in content for term in self.YELLOW_TERMS):
            return RiskLevel.YELLOW
        return RiskLevel.GREEN
