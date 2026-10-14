from datetime import UTC, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.commercial.schemas import EntitlementDecision, PlanRead, SubscriptionRead
from app.core.time import utc_now
from app.models.automation import Automation
from app.models.commercial import CommercialPlan, WorkspaceSubscription, WorkspaceUsagePeriod
from app.models.knowledge import WorkspaceMember

PLAN_DEFAULTS = (
    dict(
        code="trial",
        name="Trial",
        description="Time-limited evaluation",
        seat_limit=3,
        monthly_token_limit=100_000,
        automation_limit=5,
        storage_limit_mb=250,
        retention_days=30,
        integrations=["github"],
        support_level="self_service",
    ),
    dict(
        code="business",
        name="Business",
        description="Operational teams",
        seat_limit=25,
        monthly_token_limit=2_000_000,
        automation_limit=100,
        storage_limit_mb=10_240,
        retention_days=365,
        integrations=["github", "gmail", "google_calendar", "codex"],
        support_level="business",
    ),
    dict(
        code="enterprise",
        name="Enterprise",
        description="Configurable enterprise controls",
        seat_limit=1_000,
        monthly_token_limit=100_000_000,
        automation_limit=10_000,
        storage_limit_mb=102_400,
        retention_days=3_650,
        integrations=["github", "gmail", "google_calendar", "codex"],
        support_level="enterprise",
    ),
)


def ensure_commercial_plans(db: Session) -> None:
    existing = set(db.scalars(select(CommercialPlan.code)))
    for values in PLAN_DEFAULTS:
        if values["code"] not in existing:
            db.add(CommercialPlan(**values))


def provision_trial(db: Session, workspace_id: UUID) -> WorkspaceSubscription:
    ensure_commercial_plans(db)
    now = utc_now()
    subscription = WorkspaceSubscription(
        workspace_id=workspace_id,
        plan_code="trial",
        status="trialing",
        current_period_start=now,
        current_period_end=now + timedelta(days=14),
        trial_ends_at=now + timedelta(days=14),
    )
    db.add(subscription)
    return subscription


class CommercialService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_plans(self) -> list[PlanRead]:
        ensure_commercial_plans(self.db)
        self.db.flush()
        return [
            PlanRead.model_validate(item)
            for item in self.db.scalars(
                select(CommercialPlan)
                .where(CommercialPlan.is_public.is_(True))
                .order_by(CommercialPlan.seat_limit)
            )
        ]

    def subscription(self, workspace_id: UUID) -> SubscriptionRead:
        subscription = self.db.scalar(
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace_id)
        )
        if subscription is None:
            raise LookupError("Subscription not found")
        self._expire_if_needed(subscription)
        plan = self.db.get(CommercialPlan, subscription.plan_code)
        if plan is None:
            raise LookupError("Commercial plan not found")
        usage = self._usage(subscription)
        return SubscriptionRead(
            id=str(subscription.id),
            workspace_id=str(subscription.workspace_id),
            plan=PlanRead.model_validate(plan),
            status=subscription.status,
            billing_provider=subscription.billing_provider,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            trial_ends_at=subscription.trial_ends_at,
            cancel_at_period_end=subscription.cancel_at_period_end,
            cancelled_at=subscription.cancelled_at,
            ai_tokens_used=usage.ai_tokens if usage else 0,
            automation_runs_used=usage.automation_runs if usage else 0,
            storage_bytes_used=usage.storage_bytes if usage else 0,
        )

    def entitlement(self, workspace_id: UUID, name: str) -> EntitlementDecision:
        subscription = self.db.scalar(
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace_id)
        )
        if subscription is None:
            return EntitlementDecision(allowed=False, entitlement=name, reason="No subscription")
        self._expire_if_needed(subscription)
        if subscription.status not in {"trialing", "active"}:
            return EntitlementDecision(
                allowed=False,
                entitlement=name,
                reason=f"Subscription is {subscription.status}",
            )
        plan = self.db.get(CommercialPlan, subscription.plan_code)
        if plan is None:
            return EntitlementDecision(
                allowed=False, entitlement=name, reason="Plan is unavailable"
            )
        if name == "seats":
            used = (
                self.db.scalar(
                    select(func.count(WorkspaceMember.id)).where(
                        WorkspaceMember.workspace_id == workspace_id
                    )
                )
                or 0
            )
            return EntitlementDecision(
                allowed=used < plan.seat_limit,
                entitlement=name,
                used=used,
                limit=plan.seat_limit,
                reason=None if used < plan.seat_limit else "Seat limit reached",
            )
        if name == "automations":
            used = (
                self.db.scalar(
                    select(func.count(Automation.id)).where(Automation.workspace_id == workspace_id)
                )
                or 0
            )
            return EntitlementDecision(
                allowed=used < plan.automation_limit,
                entitlement=name,
                used=used,
                limit=plan.automation_limit,
                reason=None if used < plan.automation_limit else "Automation limit reached",
            )
        if name.startswith("integration:"):
            provider = name.partition(":")[2]
            allowed = provider in plan.integrations
            return EntitlementDecision(
                allowed=allowed,
                entitlement=name,
                reason=None if allowed else "Integration is not included in this plan",
            )
        raise ValueError("Unknown entitlement")

    def cancel(self, workspace_id: UUID) -> SubscriptionRead:
        subscription = self.db.scalar(
            select(WorkspaceSubscription)
            .where(WorkspaceSubscription.workspace_id == workspace_id)
            .with_for_update()
        )
        if subscription is None:
            raise LookupError("Subscription not found")
        subscription.cancel_at_period_end = True
        subscription.cancelled_at = utc_now()
        self.db.commit()
        return self.subscription(workspace_id)

    def _expire_if_needed(self, subscription: WorkspaceSubscription) -> None:
        period_end = subscription.current_period_end
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=UTC)
        if subscription.status == "trialing" and period_end <= utc_now():
            subscription.status = "expired"
            self.db.commit()

    def _usage(self, subscription: WorkspaceSubscription) -> WorkspaceUsagePeriod | None:
        return self.db.scalar(
            select(WorkspaceUsagePeriod).where(
                WorkspaceUsagePeriod.workspace_id == subscription.workspace_id,
                WorkspaceUsagePeriod.period_start == subscription.current_period_start,
                WorkspaceUsagePeriod.period_end == subscription.current_period_end,
            )
        )
