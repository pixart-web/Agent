import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.automations.errors import (
    AutomationConflictError,
    AutomationNotFoundError,
    AutomationValidationError,
)
from app.automations.schemas import (
    AutomationCondition,
    AutomationCreate,
    AutomationList,
    AutomationRead,
    AutomationRunList,
    AutomationRunRead,
    AutomationTrigger,
)
from app.core.time import utc_now
from app.db.session import SessionLocal
from app.execution.context_safety import sanitize_execution_payload
from app.models.automation import Automation, AutomationRun
from app.models.command import Command
from app.models.integration_account import IntegrationAccount
from app.models.outbox_event import OutboxEvent
from app.models.workflow_enums import ActorType
from app.services.audit_service import AuditService

MAX_EVENT_BYTES = 32_768


class AutomationService:
    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        self.session_factory = session_factory

    def create(self, user_id: UUID, value: AutomationCreate) -> AutomationRead:
        now = utc_now()
        if value.next_run_at is not None and self._aware(value.next_run_at) < now - timedelta(
            days=366
        ):
            raise AutomationValidationError("Scheduled automation start is too far in the past")
        automation = Automation(
            user_id=user_id,
            name=self._display(value.name),
            description=value.description,
            trigger_type=value.trigger_type,
            trigger_config=value.trigger_config,
            conditions=[item.model_dump(mode="json") for item in value.conditions],
            command_template=value.command_template.strip(),
            max_depth=value.max_depth,
            max_runs_per_window=value.max_runs_per_window,
            window_seconds=value.window_seconds,
            cooldown_seconds=value.cooldown_seconds,
            next_run_at=(
                AutomationService._aware(value.next_run_at) if value.next_run_at else None
            ),
        )
        with self.session_factory() as session:
            try:
                self._validate_integration_account(session, user_id, value)
                session.add(automation)
                session.flush()
                self._audit(
                    session,
                    actor_type=ActorType.USER,
                    actor_id=user_id,
                    event_type="automation_created",
                    resource_type="automation",
                    resource_id=automation.id,
                    correlation_id=uuid4(),
                    metadata={"trigger_type": value.trigger_type},
                )
                session.commit()
            except IntegrityError as error:
                session.rollback()
                raise AutomationConflictError(
                    "An automation with this name already exists"
                ) from error
            session.refresh(automation)
            return self._automation_output(automation)

    def list_owned(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        enabled: bool | None = None,
    ) -> AutomationList:
        with self.session_factory() as session:
            query = (
                select(Automation)
                .where(Automation.user_id == user_id)
                .order_by(Automation.updated_at.desc(), Automation.id)
                .offset(offset)
                .limit(limit)
            )
            if enabled is not None:
                query = query.where(Automation.enabled == enabled)
            values = list(session.scalars(query))
            return AutomationList(
                automations=[self._automation_output(item) for item in values],
                limit=limit,
                offset=offset,
            )

    def get_owned(self, user_id: UUID, automation_id: UUID) -> AutomationRead:
        with self.session_factory() as session:
            return self._automation_output(self._automation(session, user_id, automation_id))

    def set_enabled(self, user_id: UUID, automation_id: UUID, enabled: bool) -> AutomationRead:
        with self.session_factory() as session:
            automation = self._automation(session, user_id, automation_id, lock=True)
            automation.enabled = enabled
            correlation_id = uuid4()
            self._audit(
                session,
                actor_type=ActorType.USER,
                actor_id=user_id,
                event_type="automation_resumed" if enabled else "automation_paused",
                resource_type="automation",
                resource_id=automation.id,
                correlation_id=correlation_id,
                metadata={},
            )
            session.commit()
            return self._automation_output(automation)

    def trigger_owned(
        self,
        user_id: UUID,
        automation_id: UUID,
        value: AutomationTrigger,
    ) -> AutomationRunRead:
        with self.session_factory() as session:
            automation = self._automation(session, user_id, automation_id)
            if automation.trigger_type not in {"manual", "webhook"}:
                raise AutomationConflictError(
                    "This trigger must be emitted by its governed integration or scheduler"
                )
        return self._trigger(
            user_id=user_id,
            automation_id=automation_id,
            trigger_type=automation.trigger_type,
            event_key=value.event_key,
            payload=value.payload,
            parent_run_id=value.parent_run_id,
        )

    def dispatch_event(
        self,
        *,
        user_id: UUID,
        trigger_type: str,
        event_key: str,
        payload: dict[str, object],
        parent_run_id: UUID | None = None,
    ) -> list[AutomationRunRead]:
        with self.session_factory() as session:
            automation_ids = list(
                session.scalars(
                    select(Automation.id)
                    .where(
                        Automation.user_id == user_id,
                        Automation.trigger_type == trigger_type,
                        Automation.enabled.is_(True),
                    )
                    .order_by(Automation.id)
                )
            )
        return [
            self._trigger(
                user_id=user_id,
                automation_id=automation_id,
                trigger_type=trigger_type,
                event_key=event_key,
                payload=payload,
                parent_run_id=parent_run_id,
            )
            for automation_id in automation_ids
        ]

    def run_due_schedules(self, *, limit: int = 100) -> list[AutomationRunRead]:
        now = utc_now()
        with self.session_factory() as session:
            due = list(
                session.execute(
                    select(Automation.id, Automation.user_id, Automation.next_run_at)
                    .where(
                        Automation.trigger_type == "schedule",
                        Automation.enabled.is_(True),
                        Automation.next_run_at.is_not(None),
                        Automation.next_run_at <= now,
                    )
                    .order_by(Automation.next_run_at, Automation.id)
                    .limit(limit)
                )
            )
        results: list[AutomationRunRead] = []
        for automation_id, user_id, scheduled_for in due:
            if scheduled_for is None:
                continue
            scheduled_for = self._aware(scheduled_for)
            results.append(
                self._trigger(
                    user_id=user_id,
                    automation_id=automation_id,
                    trigger_type="schedule",
                    event_key=scheduled_for.isoformat(),
                    payload={"scheduled_for": scheduled_for.isoformat()},
                    parent_run_id=None,
                )
            )
        return results

    def recover_failed_run(self, user_id: UUID, run_id: UUID) -> AutomationRunRead:
        with self.session_factory() as session:
            failed = self._run(session, user_id, run_id)
            if failed.status != "failed":
                raise AutomationConflictError("Only failed automation runs can be recovered")
            automation_id = failed.automation_id
            trigger_type = failed.trigger_type
            payload = failed.event_payload
        return self._trigger(
            user_id=user_id,
            automation_id=automation_id,
            trigger_type=trigger_type,
            event_key=f"recovery/{run_id}",
            payload=payload,
            parent_run_id=run_id,
        )

    def complete_planning_run(self, user_id: UUID, run_id: UUID) -> None:
        with self.session_factory() as session:
            run = self._run(session, user_id, run_id, lock=True)
            if run.status != "running":
                return
            run.status = "completed"
            run.completed_at = utc_now()
            self._audit(
                session,
                actor_type=ActorType.SYSTEM,
                actor_id=None,
                event_type="automation_planning_completed",
                resource_type="automation_run",
                resource_id=run.id,
                correlation_id=run.correlation_id,
                metadata={"command_id": str(run.command_id)},
            )
            session.commit()

    def fail_planning_run(
        self,
        user_id: UUID,
        run_id: UUID,
        *,
        error_code: str,
        error_message: str,
    ) -> None:
        with self.session_factory() as session:
            run = self._run(session, user_id, run_id, lock=True)
            if run.status != "running":
                return
            run.status = "failed"
            run.error_code = error_code[:128]
            run.error_message = error_message[:500]
            run.completed_at = utc_now()
            self._audit(
                session,
                actor_type=ActorType.SYSTEM,
                actor_id=None,
                event_type="automation_planning_failed",
                resource_type="automation_run",
                resource_id=run.id,
                correlation_id=run.correlation_id,
                metadata={"error_code": run.error_code},
            )
            session.commit()

    def list_runs(
        self,
        user_id: UUID,
        *,
        automation_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AutomationRunList:
        with self.session_factory() as session:
            query = (
                select(AutomationRun)
                .where(AutomationRun.user_id == user_id)
                .order_by(AutomationRun.created_at.desc(), AutomationRun.id)
                .offset(offset)
                .limit(limit)
            )
            if automation_id is not None:
                self._automation(session, user_id, automation_id)
                query = query.where(AutomationRun.automation_id == automation_id)
            runs = list(session.scalars(query))
            return AutomationRunList(
                runs=[self._run_output(item) for item in runs],
                limit=limit,
                offset=offset,
            )

    def get_run(self, user_id: UUID, run_id: UUID) -> AutomationRunRead:
        with self.session_factory() as session:
            return self._run_output(self._run(session, user_id, run_id))

    def _trigger(
        self,
        *,
        user_id: UUID,
        automation_id: UUID,
        trigger_type: str,
        event_key: str,
        payload: dict[str, object],
        parent_run_id: UUID | None,
    ) -> AutomationRunRead:
        safe_payload = self._safe_payload(payload)
        dedupe_key = hashlib.sha256(
            f"{automation_id}:{trigger_type}:{event_key}".encode()
        ).hexdigest()
        with self.session_factory() as session:
            try:
                automation = self._automation(session, user_id, automation_id, lock=True)
                if not automation.enabled:
                    raise AutomationConflictError("Automation is paused")
                if automation.trigger_type != trigger_type:
                    raise AutomationValidationError("Trigger type does not match automation")
                existing = session.scalar(
                    select(AutomationRun).where(
                        AutomationRun.automation_id == automation_id,
                        AutomationRun.dedupe_key == dedupe_key,
                    )
                )
                if existing is not None:
                    return self._run_output(existing, deduplicated=True)

                parent = None
                depth = 0
                if parent_run_id is not None:
                    parent = self._run(session, user_id, parent_run_id)
                    depth = parent.depth + 1
                now = utc_now()
                skipped_reason = self._skip_reason(
                    session,
                    automation,
                    safe_payload,
                    depth,
                    now,
                )
                run = AutomationRun(
                    id=uuid4(),
                    user_id=user_id,
                    automation_id=automation.id,
                    trigger_type=trigger_type,
                    trigger_key=event_key,
                    dedupe_key=dedupe_key,
                    status="skipped" if skipped_reason else "running",
                    event_payload=safe_payload,
                    correlation_id=uuid4(),
                    causation_run_id=parent.id if parent else None,
                    depth=depth,
                    skipped_reason=skipped_reason,
                    completed_at=now if skipped_reason else None,
                )
                session.add(run)
                session.flush()
                if skipped_reason is None:
                    command = Command(
                        user_id=user_id,
                        input=automation.command_template,
                        correlation_id=run.correlation_id,
                    )
                    session.add(command)
                    session.flush()
                    run.command_id = command.id
                    session.add(
                        OutboxEvent(
                            event_type="automation.plan_requested",
                            aggregate_type="automation_run",
                            aggregate_id=run.id,
                            payload={
                                "command_id": str(command.id),
                                "user_id": str(user_id),
                                "run_id": str(run.id),
                            },
                        )
                    )
                    automation.last_triggered_at = now
                    self._audit(
                        session,
                        actor_type=ActorType.SYSTEM,
                        actor_id=None,
                        event_type="automation_command_created",
                        resource_type="command",
                        resource_id=command.id,
                        correlation_id=run.correlation_id,
                        metadata={
                            "automation_id": str(automation.id),
                            "automation_run_id": str(run.id),
                            "trigger_type": trigger_type,
                            "depth": depth,
                        },
                    )
                else:
                    self._audit(
                        session,
                        actor_type=ActorType.SYSTEM,
                        actor_id=None,
                        event_type="automation_run_skipped",
                        resource_type="automation_run",
                        resource_id=run.id,
                        correlation_id=run.correlation_id,
                        metadata={"reason": skipped_reason, "depth": depth},
                    )
                if trigger_type == "schedule":
                    automation.next_run_at = self._next_schedule(automation, now)
                session.commit()
                return self._run_output(run)
            except IntegrityError:
                session.rollback()

        with self.session_factory() as session:
            existing = session.scalar(
                select(AutomationRun).where(
                    AutomationRun.automation_id == automation_id,
                    AutomationRun.dedupe_key == dedupe_key,
                    AutomationRun.user_id == user_id,
                )
            )
            if existing is None:
                raise AutomationConflictError("Automation trigger conflicted with another run")
            return self._run_output(existing, deduplicated=True)

    def _skip_reason(
        self,
        session: Session,
        automation: Automation,
        payload: dict[str, object],
        depth: int,
        now: datetime,
    ) -> str | None:
        if depth > automation.max_depth:
            return "depth_limit"
        if not self._trigger_config_matches(automation, payload):
            return "trigger_config_not_matched"
        conditions = [AutomationCondition.model_validate(item) for item in automation.conditions]
        if not all(self._matches(item, payload) for item in conditions):
            return "conditions_not_met"
        if automation.last_triggered_at is not None:
            last_triggered = self._aware(automation.last_triggered_at)
            if last_triggered + timedelta(seconds=automation.cooldown_seconds) > now:
                return "cooldown"
        window_start = now - timedelta(seconds=automation.window_seconds)
        runs_in_window = session.scalar(
            select(func.count(AutomationRun.id)).where(
                AutomationRun.automation_id == automation.id,
                AutomationRun.created_at >= window_start,
                AutomationRun.status.in_(("running", "completed", "failed")),
            )
        )
        if int(runs_in_window or 0) >= automation.max_runs_per_window:
            return "execution_budget"
        return None

    @staticmethod
    def _trigger_config_matches(automation: Automation, payload: dict[str, object]) -> bool:
        config = automation.trigger_config
        direct_fields = {
            "email_received": ("account_id",),
            "calendar_event": ("account_id", "calendar_id"),
            "webhook": ("source",),
        }
        for field in direct_fields.get(automation.trigger_type, ()):
            expected = config.get(field)
            if expected is not None and payload.get(field) != expected:
                return False
        list_fields = {
            "crm_change": (("entity_types", "entity_type"), ("change_types", "change_type")),
            "task_state": (("statuses", "status"),),
        }
        for config_field, payload_field in list_fields.get(automation.trigger_type, ()):
            allowed = config.get(config_field)
            if isinstance(allowed, list) and payload.get(payload_field) not in allowed:
                return False
        return True

    @staticmethod
    def _validate_integration_account(
        session: Session,
        user_id: UUID,
        value: AutomationCreate,
    ) -> None:
        account_id = value.trigger_config.get("account_id")
        if account_id is None:
            return
        provider = {
            "email_received": "gmail",
            "calendar_event": "google_calendar",
        }.get(value.trigger_type)
        account = session.scalar(
            select(IntegrationAccount.id).where(
                IntegrationAccount.id == UUID(str(account_id)),
                IntegrationAccount.user_id == user_id,
                IntegrationAccount.provider == provider,
            )
        )
        if account is None:
            raise AutomationValidationError("Integration account is not available")

    @staticmethod
    def _matches(condition: AutomationCondition, payload: dict[str, object]) -> bool:
        found, actual = AutomationService._lookup(payload, condition.field)
        if condition.operator == "exists":
            return found
        if not found:
            return False
        if condition.operator == "eq":
            return actual == condition.value
        if condition.operator == "not_eq":
            return actual != condition.value
        return actual in condition.value if isinstance(condition.value, list) else False

    @staticmethod
    def _lookup(payload: dict[str, object], field: str) -> tuple[bool, object | None]:
        current: object = payload
        for segment in field.split("."):
            if not isinstance(current, dict) or segment not in current:
                return False, None
            current = current[segment]
        return True, current

    @staticmethod
    def _safe_payload(payload: dict[str, object]) -> dict[str, object]:
        sanitized = sanitize_execution_payload(payload)
        try:
            encoded = json.dumps(sanitized, ensure_ascii=False, sort_keys=True).encode()
        except (TypeError, ValueError) as error:
            raise AutomationValidationError("Automation event payload must be JSON") from error
        if len(encoded) > MAX_EVENT_BYTES:
            raise AutomationValidationError("Automation event payload is too large")
        return sanitized

    @staticmethod
    def _next_schedule(automation: Automation, now: datetime) -> datetime:
        interval = automation.trigger_config.get("interval_minutes")
        if not isinstance(interval, int):
            raise AutomationValidationError("Scheduled automation interval is invalid")
        next_run = AutomationService._aware(automation.next_run_at or now)
        step = timedelta(minutes=interval)
        while next_run <= now:
            next_run += step
        return next_run

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @staticmethod
    def _automation(
        session: Session,
        user_id: UUID,
        automation_id: UUID,
        *,
        lock: bool = False,
    ) -> Automation:
        query = select(Automation).where(
            Automation.id == automation_id,
            Automation.user_id == user_id,
        )
        if lock:
            query = query.with_for_update()
        automation = session.scalar(query)
        if automation is None:
            raise AutomationNotFoundError("Automation was not found")
        return automation

    @staticmethod
    def _run(
        session: Session,
        user_id: UUID,
        run_id: UUID,
        *,
        lock: bool = False,
    ) -> AutomationRun:
        query = select(AutomationRun).where(
            AutomationRun.id == run_id,
            AutomationRun.user_id == user_id,
        )
        if lock:
            query = query.with_for_update()
        run = session.scalar(query)
        if run is None:
            raise AutomationNotFoundError("Automation run was not found")
        return run

    @staticmethod
    def _automation_output(value: Automation) -> AutomationRead:
        return AutomationRead(
            id=value.id,
            user_id=value.user_id,
            name=value.name,
            description=value.description,
            enabled=value.enabled,
            trigger_type=value.trigger_type,
            trigger_config=value.trigger_config,
            conditions=[AutomationCondition.model_validate(item) for item in value.conditions],
            command_template=value.command_template,
            max_depth=value.max_depth,
            max_runs_per_window=value.max_runs_per_window,
            window_seconds=value.window_seconds,
            cooldown_seconds=value.cooldown_seconds,
            next_run_at=(
                AutomationService._aware(value.next_run_at) if value.next_run_at else None
            ),
            last_triggered_at=(
                AutomationService._aware(value.last_triggered_at)
                if value.last_triggered_at
                else None
            ),
            created_at=AutomationService._aware(value.created_at),
            updated_at=AutomationService._aware(value.updated_at),
        )

    @staticmethod
    def _run_output(value: AutomationRun, *, deduplicated: bool = False) -> AutomationRunRead:
        return AutomationRunRead(
            id=value.id,
            automation_id=value.automation_id,
            trigger_type=value.trigger_type,
            trigger_key=value.trigger_key,
            status=value.status,
            correlation_id=value.correlation_id,
            causation_run_id=value.causation_run_id,
            depth=value.depth,
            command_id=value.command_id,
            skipped_reason=value.skipped_reason,
            error_code=value.error_code,
            error_message=value.error_message,
            created_at=AutomationService._aware(value.created_at),
            completed_at=(
                AutomationService._aware(value.completed_at) if value.completed_at else None
            ),
            deduplicated=deduplicated,
        )

    @staticmethod
    def _display(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _audit(
        session: Session,
        *,
        actor_type: ActorType,
        actor_id: UUID | None,
        event_type: str,
        resource_type: str,
        resource_id: UUID,
        correlation_id: UUID,
        metadata: dict[str, object],
    ) -> None:
        AuditService(session).record(
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            correlation_id=correlation_id,
        )
