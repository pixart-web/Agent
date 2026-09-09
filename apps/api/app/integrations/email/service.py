from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.db.session import SessionLocal
from app.execution.context import ExecutionContext
from app.integrations.email.base import EmailProvider
from app.integrations.email.credentials import FernetSecretStore, SecretStore
from app.integrations.email.errors import (
    EmailAuthenticationError,
    EmailDeliveryUnknownError,
    EmailNotFoundError,
    EmailPermissionError,
    EmailValidationError,
)
from app.integrations.email.oauth import GmailOAuthClient
from app.integrations.email.policy import EmailPolicy
from app.integrations.email.providers.gmail import GmailProvider
from app.integrations.email.schemas import (
    EmailListInput,
    EmailMarkReadInput,
    EmailMarkReadOutput,
    EmailMessageInput,
    EmailMessageOutput,
    EmailMessagesOutput,
    EmailReplyInput,
    EmailSearchInput,
    EmailSendInput,
    EmailThreadInput,
    EmailThreadOutput,
    EmailWriteOutput,
)
from app.models.email_send_record import EmailSendRecord
from app.models.integration_account import IntegrationAccount
from app.models.task_action import TaskAction
from app.models.workflow_enums import ActorType, EmailSendStatus, IntegrationAccountStatus
from app.repositories.integration_account_repository import IntegrationAccountRepository
from app.services.audit_service import AuditService

ProviderFactory = Callable[[str, Settings, EmailPolicy], EmailProvider]


def build_email_provider(token: str, settings: Settings, policy: EmailPolicy) -> EmailProvider:
    return GmailProvider(
        token,
        settings.email_api_timeout_seconds,
        max_body_chars=settings.email_max_body_chars,
        policy=policy,
    )


class EmailService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        session_factory: sessionmaker[Session] = SessionLocal,
        secret_store: SecretStore | None = None,
        provider_factory: ProviderFactory = build_email_provider,
        oauth: GmailOAuthClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.session_factory = session_factory
        key = self.settings.integration_encryption_key
        self.secret_store = secret_store or (
            FernetSecretStore(key.get_secret_value()) if key else None
        )
        self.provider_factory = provider_factory
        self.oauth = oauth or GmailOAuthClient(self.settings)
        self.policy = EmailPolicy(
            self.settings.email_allowed_account_list,
            max_recipients=self.settings.email_max_recipients,
            max_attachment_bytes=self.settings.email_max_attachment_bytes,
        )

    def list_messages(
        self, context: ExecutionContext, value: EmailListInput
    ) -> EmailMessagesOutput:
        def operation(provider: EmailProvider) -> EmailMessagesOutput:
            page = provider.list_messages(self._limit(value.limit), value.page_token)
            return EmailMessagesOutput(messages=page.messages, next_page_token=page.next_page_token)

        return self._read(context, value.account_id, "email_messages_listed", operation)

    def search(self, context: ExecutionContext, value: EmailSearchInput) -> EmailMessagesOutput:
        def operation(provider: EmailProvider) -> EmailMessagesOutput:
            page = provider.search(value.query, self._limit(value.limit), value.page_token)
            return EmailMessagesOutput(messages=page.messages, next_page_token=page.next_page_token)

        return self._read(context, value.account_id, "email_searched", operation)

    def get_message(
        self, context: ExecutionContext, value: EmailMessageInput
    ) -> EmailMessageOutput:
        return self._read(
            context,
            value.account_id,
            "email_message_read",
            lambda provider: EmailMessageOutput(message=provider.get_message(value.message_id)),
        )

    def get_thread(self, context: ExecutionContext, value: EmailThreadInput) -> EmailThreadOutput:
        return self._read(
            context,
            value.account_id,
            "email_thread_read",
            lambda provider: EmailThreadOutput(thread=provider.get_thread(value.thread_id)),
        )

    def mark_read(
        self, context: ExecutionContext, value: EmailMarkReadInput
    ) -> EmailMarkReadOutput:
        if not self.settings.email_mark_read_enabled:
            raise EmailPermissionError("Mark-read capability is disabled")

        def operation(provider: EmailProvider) -> EmailMarkReadOutput:
            provider.mark_read(value.message_id, value.read)
            return EmailMarkReadOutput(message_id=value.message_id, read=value.read)

        return self._read(context, value.account_id, "email_marked_read", operation)

    def send(self, context: ExecutionContext, value: EmailSendInput) -> EmailWriteOutput:
        if not self.settings.email_send_enabled:
            raise EmailPermissionError("Email sending is disabled")
        recipients = self.policy.recipients(value.to, value.cc, value.bcc)
        self._body(value.body)
        self.policy.classify(value.subject, value.body)
        return self._write(
            context,
            value.account_id,
            value.model_dump(mode="json"),
            "email_send_requested",
            "email_sent",
            lambda provider, account, key: provider.send(
                sender=account.email_address,
                to=[str(item.address) for item in value.to],
                cc=[str(item.address) for item in value.cc],
                bcc=[str(item.address) for item in value.bcc],
                subject=value.subject,
                body=value.body,
                idempotency_key=key,
            ),
            recipient_count=len(recipients),
        )

    def reply(self, context: ExecutionContext, value: EmailReplyInput) -> EmailWriteOutput:
        if not self.settings.email_send_enabled:
            raise EmailPermissionError("Email sending is disabled")
        self._body(value.body)
        self.policy.classify("", value.body)
        return self._write(
            context,
            value.account_id,
            value.model_dump(mode="json"),
            "email_reply_requested",
            "email_replied",
            lambda provider, account, key: provider.reply(
                sender=account.email_address,
                original=provider.get_message(value.message_id),
                body=value.body,
                idempotency_key=key,
            ),
            recipient_count=1,
        )

    def _read(self, context: ExecutionContext, account_id: UUID, event: str, operation):
        self._ensure_enabled()
        with self.session_factory() as session:
            account = self._owned(session, account_id, context.user_id)
            try:
                provider = self._provider(account)
            except EmailAuthenticationError:
                account.status = IntegrationAccountStatus.EXPIRED
                self._audit(session, context, "email_auth_failed", account, {})
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
        account_id: UUID,
        payload: dict[str, object],
        requested_event: str,
        success_event: str,
        operation,
        *,
        recipient_count: int,
    ) -> EmailWriteOutput:
        self._ensure_enabled()
        with self.session_factory() as session:
            action = session.get(TaskAction, context.action_id)
            if action is None or action.input_payload != payload:
                raise EmailValidationError(
                    "Email payload does not match the approved execution action"
                )
            fingerprint = action.action_fingerprint
            key = f"{context.action_id}:{fingerprint}"
            account = self._owned(session, account_id, context.user_id)
            existing = (
                session.query(EmailSendRecord)
                .filter_by(task_action_id=context.action_id)
                .one_or_none()
            )
            if existing:
                if existing.payload_fingerprint != fingerprint:
                    raise EmailValidationError("Email action payload changed after approval")
                if existing.status == EmailSendStatus.SENT:
                    return EmailWriteOutput(
                        message_id=existing.provider_message_id or "",
                        thread_id=existing.thread_id,
                        status="sent",
                    )
                raise EmailDeliveryUnknownError(
                    "Email was already attempted; automatic retry is prohibited"
                )
            record = EmailSendRecord(
                user_id=context.user_id,
                account_id=account.id,
                task_action_id=context.action_id,
                task_execution_id=context.execution_id,
                idempotency_key=key,
                payload_fingerprint=fingerprint,
                status=EmailSendStatus.PENDING,
            )
            session.add(record)
            self._audit(
                session, context, requested_event, account, {"recipient_count": recipient_count}
            )
            session.commit()
            try:
                provider = self._provider(account)
            except EmailAuthenticationError:
                record.status = EmailSendStatus.FAILED
                record.error_code = "email_auth_failed"
                account.status = IntegrationAccountStatus.EXPIRED
                self._audit(session, context, "email_auth_failed", account, {})
                session.commit()
                raise
            try:
                output = operation(provider, account, key)
            except EmailDeliveryUnknownError:
                record.status = EmailSendStatus.DELIVERY_UNKNOWN
                record.error_code = "delivery_unknown"
                self._audit(session, context, "email_delivery_unknown", account, {})
                session.commit()
                raise
            except Exception as error:
                record.status = EmailSendStatus.FAILED
                record.error_code = getattr(error, "code", "email_write_failed")
                self._audit(session, context, "email_write_failed", account, {})
                session.commit()
                raise
            finally:
                provider.close()
            record.status = EmailSendStatus.SENT
            record.provider_message_id = output.message_id
            record.thread_id = output.thread_id
            record.sent_at = utc_now()
            self._audit(
                session, context, success_event, account, {"recipient_count": recipient_count}
            )
            session.commit()
            return output

    def _provider(self, account: IntegrationAccount) -> EmailProvider:
        if not self.secret_store:
            raise EmailAuthenticationError("Email credential encryption is not configured")
        secrets = self.secret_store.decrypt(account.encrypted_credentials)
        refresh_token = secrets.get("refresh_token")
        if not isinstance(refresh_token, str):
            raise EmailAuthenticationError("Email account has no refresh token")
        token = self.oauth.refresh(refresh_token)
        return self.provider_factory(token, self.settings, self.policy)

    def _owned(self, session: Session, account_id: UUID, user_id: UUID) -> IntegrationAccount:
        account = IntegrationAccountRepository(session).get_owned(account_id, user_id)
        if not account:
            raise EmailNotFoundError("Email account was not found")
        if account.status != IntegrationAccountStatus.CONNECTED:
            raise EmailAuthenticationError("Email account is not connected")
        self.policy.authorize_account(account.email_address)
        return account

    def _limit(self, requested: int) -> int:
        if requested > self.settings.email_max_search_results:
            raise EmailValidationError("Email result limit exceeds the configured maximum")
        return requested

    def _body(self, value: str) -> None:
        if len(value) > self.settings.email_max_body_chars:
            raise EmailValidationError("Email body exceeds the configured maximum")

    def _ensure_enabled(self) -> None:
        if not self.settings.email_integration_enabled:
            raise EmailPermissionError("Email integration is disabled")

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
