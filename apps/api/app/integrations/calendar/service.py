from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.db.session import SessionLocal
from app.execution.context import ExecutionContext
from app.integrations.calendar.base import CalendarProvider
from app.integrations.calendar.errors import (
    CalendarAuthenticationError,
    CalendarDeliveryUnknownError,
    CalendarNotFoundError,
    CalendarPermissionError,
    CalendarValidationError,
)
from app.integrations.calendar.oauth import GoogleCalendarOAuthClient
from app.integrations.calendar.policy import CalendarPolicy
from app.integrations.calendar.providers.google import GoogleCalendarProvider
from app.integrations.calendar.schemas import (
    CalendarAvailabilityInput,
    CalendarAvailabilityOutput,
    CalendarCancelEventInput,
    CalendarCreateEventInput,
    CalendarEventInput,
    CalendarEventOutput,
    CalendarEventsInput,
    CalendarEventsOutput,
    CalendarListInput,
    CalendarListOutput,
    CalendarSearchInput,
    CalendarUpdateEventInput,
    CalendarWriteOutput,
)
from app.integrations.email.credentials import FernetSecretStore, SecretStore
from app.models.calendar_reference import CalendarReference
from app.models.calendar_write_record import CalendarWriteRecord
from app.models.command import Command
from app.models.integration_account import IntegrationAccount
from app.models.task import Task
from app.models.task_action import TaskAction
from app.models.workflow_enums import (
    ActorType,
    CalendarWriteStatus,
    IntegrationAccountStatus,
)
from app.repositories.integration_account_repository import IntegrationAccountRepository
from app.services.audit_service import AuditService

ProviderFactory = Callable[[str, Settings, CalendarPolicy], CalendarProvider]
OutputT = TypeVar("OutputT")


def build_calendar_provider(
    token: str, settings: Settings, policy: CalendarPolicy
) -> CalendarProvider:
    return GoogleCalendarProvider(
        token,
        settings.calendar_api_timeout_seconds,
        policy=policy,
    )


class CalendarService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        session_factory: sessionmaker[Session] = SessionLocal,
        secret_store: SecretStore | None = None,
        provider_factory: ProviderFactory = build_calendar_provider,
        oauth: GoogleCalendarOAuthClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.session_factory = session_factory
        key = self.settings.integration_encryption_key
        self.secret_store = secret_store or (
            FernetSecretStore(key.get_secret_value()) if key else None
        )
        self.provider_factory = provider_factory
        self.oauth = oauth or GoogleCalendarOAuthClient(self.settings)
        self.policy = CalendarPolicy(
            self.settings.calendar_allowed_account_list,
            self.settings.calendar_internal_domain_list,
            self.settings.calendar_max_attendees,
        )

    def list_calendars(
        self, context: ExecutionContext, value: CalendarListInput
    ) -> CalendarListOutput:
        def operation(provider: CalendarProvider) -> CalendarListOutput:
            page = provider.list_calendars(self._limit(value.limit), value.page_token)
            return CalendarListOutput(
                calendars=page.calendars, next_page_token=page.next_page_token
            )

        return self._read(context, value.account_id, "calendars_listed", operation)

    def list_events(
        self, context: ExecutionContext, value: CalendarEventsInput
    ) -> CalendarEventsOutput:
        def operation(provider: CalendarProvider) -> CalendarEventsOutput:
            page = provider.list_events(
                value.calendar_id,
                value.time_min,
                value.time_max,
                self._limit(value.limit),
                value.page_token,
            )
            return CalendarEventsOutput(events=page.events, next_page_token=page.next_page_token)

        return self._read(context, value.account_id, "calendar_events_listed", operation)

    def search_events(
        self, context: ExecutionContext, value: CalendarSearchInput
    ) -> CalendarEventsOutput:
        def operation(provider: CalendarProvider) -> CalendarEventsOutput:
            page = provider.list_events(
                value.calendar_id,
                value.time_min,
                value.time_max,
                self._limit(value.limit),
                value.page_token,
                value.query,
            )
            return CalendarEventsOutput(events=page.events, next_page_token=page.next_page_token)

        return self._read(context, value.account_id, "calendar_events_searched", operation)

    def get_event(
        self, context: ExecutionContext, value: CalendarEventInput
    ) -> CalendarEventOutput:
        def operation(provider: CalendarProvider) -> CalendarEventOutput:
            return CalendarEventOutput(event=provider.get_event(value.calendar_id, value.event_id))

        output = self._read(context, value.account_id, "calendar_event_read", operation)
        self._reference(context, value.account_id, value.calendar_id, value.event_id)
        return output

    def get_availability(
        self, context: ExecutionContext, value: CalendarAvailabilityInput
    ) -> CalendarAvailabilityOutput:
        return self._read(
            context,
            value.account_id,
            "calendar_availability_read",
            lambda provider: CalendarAvailabilityOutput(calendars=provider.get_availability(value)),
        )

    def create_event(
        self, context: ExecutionContext, value: CalendarCreateEventInput
    ) -> CalendarWriteOutput:
        _, external = self.policy.attendees([str(item) for item in value.attendees])
        return self._write(
            context,
            value,
            "create",
            lambda provider, key: provider.create_event(value, key),
            external_attendees=external,
        )

    def update_event(
        self, context: ExecutionContext, value: CalendarUpdateEventInput
    ) -> CalendarWriteOutput:
        _, external = self.policy.attendees([str(item) for item in value.attendees])
        return self._write(
            context,
            value,
            "update",
            lambda provider, key: provider.update_event(value, key),
            external_attendees=external,
        )

    def cancel_event(
        self, context: ExecutionContext, value: CalendarCancelEventInput
    ) -> CalendarWriteOutput:
        return self._write(
            context,
            value,
            "cancel",
            lambda provider, key: provider.cancel_event(value, key),
            external_attendees=[],
        )

    def _read(
        self,
        context: ExecutionContext,
        account_id: UUID,
        event: str,
        operation: Callable[[CalendarProvider], OutputT],
    ) -> OutputT:
        self._ensure_enabled()
        with self.session_factory() as session:
            account = self._owned(session, account_id, context.user_id)
            try:
                provider = self._provider(account)
            except CalendarAuthenticationError:
                account.status = IntegrationAccountStatus.EXPIRED
                self._audit(session, context, "calendar_auth_failed", account, {})
                session.commit()
                raise
            try:
                output = operation(provider)
                account.last_sync_at = utc_now()
                self._audit(session, context, event, account, {})
                session.commit()
                return output
            finally:
                provider.close()

    def _write(
        self,
        context: ExecutionContext,
        value: CalendarCreateEventInput | CalendarUpdateEventInput | CalendarCancelEventInput,
        operation_name: str,
        operation: Callable[[CalendarProvider, str], CalendarWriteOutput],
        *,
        external_attendees: list[str],
    ) -> CalendarWriteOutput:
        self._ensure_enabled()
        if not self.settings.calendar_write_enabled:
            raise CalendarPermissionError("Calendar writes are disabled")
        payload = value.model_dump(mode="json")
        with self.session_factory() as session:
            action = session.scalar(
                select(TaskAction).where(TaskAction.id == context.action_id).with_for_update()
            )
            if action is None or action.input_payload != payload:
                raise CalendarValidationError(
                    "Calendar payload does not match the approved execution action"
                )
            fingerprint = action.action_fingerprint
            key = f"{context.action_id}:{fingerprint}"
            account = self._owned(session, value.account_id, context.user_id)
            existing = session.scalar(
                select(CalendarWriteRecord).where(
                    CalendarWriteRecord.task_action_id == context.action_id
                )
            )
            if existing:
                if existing.payload_fingerprint != fingerprint:
                    raise CalendarValidationError("Calendar action payload changed after approval")
                if existing.status == CalendarWriteStatus.SUCCEEDED:
                    return CalendarWriteOutput(
                        event_id=existing.provider_event_id or "",
                        calendar_id=existing.calendar_id or value.calendar_id,
                        status="succeeded",
                    )
                raise CalendarDeliveryUnknownError(
                    "Calendar write was already attempted; automatic retry is prohibited"
                )
            record = CalendarWriteRecord(
                user_id=context.user_id,
                account_id=account.id,
                task_action_id=context.action_id,
                task_execution_id=context.execution_id,
                operation=operation_name,
                idempotency_key=key,
                payload_fingerprint=fingerprint,
                status=CalendarWriteStatus.PENDING,
                calendar_id=value.calendar_id,
                provider_event_id=getattr(value, "event_id", None),
            )
            session.add(record)
            self._audit(
                session,
                context,
                f"calendar_event_{operation_name}_requested",
                account,
                self._preview(value, external_attendees),
            )
            session.commit()
            try:
                provider = self._provider(account)
            except CalendarAuthenticationError:
                record.status = CalendarWriteStatus.FAILED
                record.error_code = "calendar_auth_failed"
                account.status = IntegrationAccountStatus.EXPIRED
                self._audit(session, context, "calendar_auth_failed", account, {})
                session.commit()
                raise
            try:
                output = operation(provider, key)
            except CalendarDeliveryUnknownError:
                record.status = CalendarWriteStatus.DELIVERY_UNKNOWN
                record.error_code = "delivery_unknown"
                self._audit(session, context, "calendar_delivery_unknown", account, {})
                session.commit()
                raise
            except Exception as error:
                record.status = CalendarWriteStatus.FAILED
                record.error_code = getattr(error, "code", "calendar_write_failed")
                self._audit(session, context, "calendar_write_failed", account, {})
                session.commit()
                raise
            finally:
                provider.close()
            record.status = CalendarWriteStatus.SUCCEEDED
            record.calendar_id = output.calendar_id
            record.provider_event_id = output.event_id
            record.completed_at = utc_now()
            self._add_reference(
                session,
                context,
                account.id,
                output.calendar_id,
                output.event_id,
            )
            self._audit(
                session,
                context,
                f"calendar_event_{operation_name}d",
                account,
                self._preview(value, external_attendees),
            )
            session.commit()
            return output

    def _provider(self, account: IntegrationAccount) -> CalendarProvider:
        if not self.secret_store:
            raise CalendarAuthenticationError("Calendar credential encryption is not configured")
        secrets = self.secret_store.decrypt(account.encrypted_credentials)
        refresh_token = secrets.get("refresh_token")
        if not isinstance(refresh_token, str):
            raise CalendarAuthenticationError("Calendar account has no refresh token")
        token = self.oauth.refresh(refresh_token)
        return self.provider_factory(token, self.settings, self.policy)

    def _owned(self, session: Session, account_id: UUID, user_id: UUID) -> IntegrationAccount:
        account = IntegrationAccountRepository(session).get_owned(
            account_id, user_id, "google_calendar"
        )
        if account is None:
            raise CalendarNotFoundError("Calendar account was not found")
        if account.status != IntegrationAccountStatus.CONNECTED:
            raise CalendarAuthenticationError("Calendar account is not connected")
        self.policy.authorize_account(account.email_address)
        return account

    def _limit(self, requested: int) -> int:
        if requested > self.settings.calendar_max_results:
            raise CalendarValidationError("Calendar result limit exceeds the configured maximum")
        return requested

    def _ensure_enabled(self) -> None:
        if not self.settings.calendar_integration_enabled:
            raise CalendarPermissionError("Calendar integration is disabled")

    def _reference(
        self,
        context: ExecutionContext,
        account_id: UUID,
        calendar_id: str,
        event_id: str,
    ) -> None:
        with self.session_factory() as session:
            self._add_reference(session, context, account_id, calendar_id, event_id)
            session.commit()

    @staticmethod
    def _add_reference(
        session: Session,
        context: ExecutionContext,
        account_id: UUID,
        calendar_id: str,
        event_id: str,
    ) -> None:
        existing = session.scalar(
            select(CalendarReference).where(
                CalendarReference.account_id == account_id,
                CalendarReference.calendar_id == calendar_id,
                CalendarReference.event_id == event_id,
            )
        )
        if existing is None:
            session.add(
                CalendarReference(
                    provider="google_calendar",
                    account_id=account_id,
                    calendar_id=calendar_id,
                    event_id=event_id,
                    task_id=context.task_id if session.get(Task, context.task_id) else None,
                    command_id=(
                        context.command_id if session.get(Command, context.command_id) else None
                    ),
                )
            )

    @staticmethod
    def _preview(
        value: CalendarCreateEventInput | CalendarUpdateEventInput | CalendarCancelEventInput,
        external_attendees: list[str],
    ) -> dict[str, object]:
        return {
            "calendar_id": value.calendar_id,
            "event_id": getattr(value, "event_id", None),
            "title": getattr(value, "title", None),
            "start": getattr(value, "start", None).model_dump(mode="json")
            if hasattr(value, "start")
            else None,
            "end": getattr(value, "end", None).model_dump(mode="json")
            if hasattr(value, "end")
            else None,
            "attendee_count": len(getattr(value, "attendees", [])),
            "external_attendees": external_attendees,
        }

    @staticmethod
    def _audit(
        session: Session,
        context: ExecutionContext,
        event: str,
        account: IntegrationAccount,
        metadata: dict[str, object],
    ) -> None:
        AuditService(session).record(
            actor_type=ActorType.WORKER,
            actor_id=context.user_id,
            event_type=event,
            resource_type="integration_account",
            resource_id=account.id,
            metadata={"provider": account.provider, **metadata},
            correlation_id=context.correlation_id,
        )
