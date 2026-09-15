from collections.abc import Iterable

from app.integrations.email.base import EmailPage
from app.integrations.email.errors import EmailDeliveryUnknownError, EmailNotFoundError
from app.integrations.email.schemas import (
    EmailMessage,
    EmailMessageSummary,
    EmailThread,
    EmailWriteOutput,
)


class FakeEmailProvider:
    def __init__(
        self,
        messages: Iterable[EmailMessage] = (),
        *,
        delivery_unknown: bool = False,
    ) -> None:
        self.messages = {message.id: message for message in messages}
        self.sent: list[dict[str, object]] = []
        self.delivery_unknown = delivery_unknown

    def list_messages(self, limit: int, page_token: str | None = None) -> EmailPage:
        del page_token
        return EmailPage(
            messages=[self._summary(value) for value in self.messages.values()][:limit]
        )

    def search(self, query: str, limit: int, page_token: str | None = None) -> EmailPage:
        del page_token
        needle = query.lower()
        values = [
            value
            for value in self.messages.values()
            if needle in value.subject.lower() or needle in value.text_body.lower()
        ]
        return EmailPage(messages=[self._summary(value) for value in values[:limit]])

    def get_message(self, message_id: str) -> EmailMessage:
        try:
            return self.messages[message_id]
        except KeyError as error:
            raise EmailNotFoundError("Email message was not found") from error

    def get_thread(self, thread_id: str) -> EmailThread:
        values = [value for value in self.messages.values() if value.thread_id == thread_id]
        if not values:
            raise EmailNotFoundError("Email thread was not found")
        return EmailThread(id=thread_id, messages=values)

    def send(self, **kwargs: object) -> EmailWriteOutput:
        if self.delivery_unknown:
            raise EmailDeliveryUnknownError("Email delivery is unknown; operator review required")
        self.sent.append(kwargs)
        identifier = f"sent-{len(self.sent)}"
        return EmailWriteOutput(message_id=identifier, thread_id=identifier, status="sent")

    def reply(self, **kwargs: object) -> EmailWriteOutput:
        if self.delivery_unknown:
            raise EmailDeliveryUnknownError("Email delivery is unknown; operator review required")
        self.sent.append(kwargs)
        original = kwargs["original"]
        identifier = f"reply-{len(self.sent)}"
        return EmailWriteOutput(message_id=identifier, thread_id=original.thread_id, status="sent")

    def mark_read(self, message_id: str, read: bool) -> None:
        value = self.get_message(message_id)
        self.messages[message_id] = value.model_copy(update={"unread": not read})

    def close(self) -> None:
        return None

    @staticmethod
    def _summary(value: EmailMessage) -> EmailMessageSummary:
        return EmailMessageSummary.model_validate(
            value.model_dump(
                exclude={
                    "cc",
                    "reply_to",
                    "text_body",
                    "body_truncated",
                    "attachments",
                    "provider_headers",
                }
            )
        )
