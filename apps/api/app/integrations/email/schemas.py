from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmailAddress(StrictModel):
    address: EmailStr
    name: str | None = Field(default=None, max_length=200)


class EmailAttachmentMetadata(StrictModel):
    attachment_id: str | None = None
    filename: str = Field(max_length=500)
    mime_type: str = Field(max_length=255)
    size: int = Field(ge=0)
    blocked: bool = False


class EmailMessageSummary(StrictModel):
    id: str
    thread_id: str
    subject: str
    sender: EmailAddress
    recipients: list[EmailAddress] = Field(default_factory=list)
    sent_at: datetime | None = None
    snippet: str = ""
    unread: bool = False
    has_attachments: bool = False
    external_content: bool = True
    trust: Literal["untrusted"] = "untrusted"


class EmailMessage(EmailMessageSummary):
    cc: list[EmailAddress] = Field(default_factory=list)
    reply_to: list[EmailAddress] = Field(default_factory=list)
    text_body: str = ""
    body_truncated: bool = False
    attachments: list[EmailAttachmentMetadata] = Field(default_factory=list)
    provider_headers: dict[str, str] = Field(default_factory=dict)


class EmailThread(StrictModel):
    id: str
    messages: list[EmailMessage]


class EmailListInput(StrictModel):
    account_id: UUID
    limit: int = Field(default=25, ge=1, le=100)
    page_token: str | None = None


class EmailSearchInput(EmailListInput):
    query: str = Field(min_length=1, max_length=500)


class EmailMessageInput(StrictModel):
    account_id: UUID
    message_id: str = Field(min_length=1, max_length=500)


class EmailThreadInput(StrictModel):
    account_id: UUID
    thread_id: str = Field(min_length=1, max_length=500)


class EmailSendInput(StrictModel):
    account_id: UUID
    to: list[EmailAddress] = Field(min_length=1)
    cc: list[EmailAddress] = Field(default_factory=list)
    bcc: list[EmailAddress] = Field(default_factory=list)
    subject: str = Field(min_length=1, max_length=998)
    body: str = Field(min_length=1, max_length=50_000)


class EmailReplyInput(StrictModel):
    account_id: UUID
    message_id: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=50_000)


class EmailMarkReadInput(StrictModel):
    account_id: UUID
    message_id: str = Field(min_length=1, max_length=500)
    read: bool = True


class EmailMessagesOutput(StrictModel):
    messages: list[EmailMessageSummary]
    next_page_token: str | None = None


class EmailMessageOutput(StrictModel):
    message: EmailMessage


class EmailThreadOutput(StrictModel):
    thread: EmailThread


class EmailWriteOutput(StrictModel):
    message_id: str
    thread_id: str | None = None
    status: str


class EmailMarkReadOutput(StrictModel):
    message_id: str
    read: bool


class EmailAccountOutput(StrictModel):
    id: UUID
    provider: str
    account_type: str
    email_address: EmailStr
    status: str
    scopes: list[str]
    last_sync_at: datetime | None
