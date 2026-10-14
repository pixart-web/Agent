from typing import Protocol


class BillingUnavailableError(RuntimeError):
    pass


class BillingProvider(Protocol):
    def create_checkout(self, *, workspace_id: str, plan_code: str) -> str: ...

    def cancel_subscription(self, *, provider_subscription_id: str) -> None: ...


class DisabledBillingProvider:
    """Fail-closed provider used until commercial credentials are explicitly authorized."""

    def create_checkout(self, *, workspace_id: str, plan_code: str) -> str:
        raise BillingUnavailableError("Billing provider is not configured")

    def cancel_subscription(self, *, provider_subscription_id: str) -> None:
        raise BillingUnavailableError("Billing provider is not configured")
