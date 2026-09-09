from dataclasses import dataclass
from typing import Protocol

from app.integrations.email.schemas import (
    EmailMessage,
    EmailMessageSummary,
    EmailThread,
    EmailWriteOutput,
)


@dataclass(frozen=True)
class EmailPage:
    messages: list[EmailMessageSummary]
    next_page_token: str | None = None


class EmailProvider(Protocol):
    def list_messages(self, limit: int, page_token: str | None = None) -> EmailPage: ...
    def search(self, query: str, limit: int, page_token: str | None = None) -> EmailPage: ...
    def get_message(self, message_id: str) -> EmailMessage: ...
    def get_thread(self, thread_id: str) -> EmailThread: ...
    def send(
        self,
        *,
        sender: str,
        to: list[str],
        cc: list[str],
        bcc: list[str],
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> EmailWriteOutput: ...
    def reply(
        self,
        *,
        sender: str,
        original: EmailMessage,
        body: str,
        idempotency_key: str,
    ) -> EmailWriteOutput: ...
    def mark_read(self, message_id: str, read: bool) -> None: ...
    def close(self) -> None: ...
