import base64
import html
import re
from datetime import UTC, datetime
from email.message import EmailMessage as MimeMessage
from email.utils import getaddresses, parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any

import httpx

from app.integrations.email.base import EmailPage
from app.integrations.email.errors import (
    EmailAuthenticationError,
    EmailDeliveryUnknownError,
    EmailNotFoundError,
    EmailPermissionError,
    EmailRateLimitError,
    EmailTimeoutError,
    EmailTransientError,
    EmailValidationError,
)
from app.integrations.email.policy import EmailPolicy
from app.integrations.email.schemas import (
    EmailAddress,
    EmailAttachmentMetadata,
    EmailMessage,
    EmailMessageSummary,
    EmailThread,
    EmailWriteOutput,
)

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self.parts)).strip()


class GmailProvider:
    def __init__(
        self,
        access_token: str,
        timeout_seconds: float,
        *,
        max_body_chars: int,
        policy: EmailPolicy,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.client = httpx.Client(
            base_url=GMAIL_API,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=timeout_seconds,
            transport=transport,
        )
        self.max_body_chars = max_body_chars
        self.policy = policy

    def profile(self) -> dict[str, object]:
        return self._request("GET", "/profile")

    def list_messages(self, limit: int, page_token: str | None = None) -> EmailPage:
        return self._list(None, limit, page_token)

    def search(self, query: str, limit: int, page_token: str | None = None) -> EmailPage:
        return self._list(query, limit, page_token)

    def _list(self, query: str | None, limit: int, page_token: str | None) -> EmailPage:
        params: dict[str, object] = {"maxResults": limit}
        if query:
            params["q"] = query
        if page_token:
            params["pageToken"] = page_token
        payload = self._request("GET", "/messages", params=params)
        messages = [
            self._summary(
                self._request(
                    "GET",
                    f"/messages/{item['id']}",
                    params={"format": "metadata"},
                )
            )
            for item in payload.get("messages", [])
        ]
        return EmailPage(messages=messages, next_page_token=payload.get("nextPageToken"))

    def get_message(self, message_id: str) -> EmailMessage:
        return self._message(
            self._request("GET", f"/messages/{message_id}", params={"format": "full"})
        )

    def get_thread(self, thread_id: str) -> EmailThread:
        payload = self._request("GET", f"/threads/{thread_id}", params={"format": "full"})
        return EmailThread(
            id=str(payload["id"]),
            messages=[self._message(item) for item in payload.get("messages", [])],
        )

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
    ) -> EmailWriteOutput:
        message = MimeMessage()
        message["From"] = sender
        message["To"] = ", ".join(to)
        if cc:
            message["Cc"] = ", ".join(cc)
        if bcc:
            message["Bcc"] = ", ".join(bcc)
        message["Subject"] = subject
        message["X-Kiko-Idempotency-Key"] = idempotency_key
        message.set_content(body)
        return self._send_raw(message)

    def reply(
        self,
        *,
        sender: str,
        original: EmailMessage,
        body: str,
        idempotency_key: str,
    ) -> EmailWriteOutput:
        recipients = original.reply_to or [original.sender]
        message = MimeMessage()
        message["From"] = sender
        message["To"] = ", ".join(str(value.address) for value in recipients)
        subject = original.subject
        message["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        provider_id = original.provider_headers.get("message-id")
        if provider_id:
            message["In-Reply-To"] = provider_id
            message["References"] = provider_id
        message["X-Kiko-Idempotency-Key"] = idempotency_key
        message.set_content(body)
        return self._send_raw(message, thread_id=original.thread_id)

    def _send_raw(self, message: MimeMessage, thread_id: str | None = None) -> EmailWriteOutput:
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
        body: dict[str, object] = {"raw": raw}
        if thread_id:
            body["threadId"] = thread_id
        try:
            payload = self._request("POST", "/messages/send", json=body)
        except (EmailTimeoutError, EmailTransientError) as error:
            raise EmailDeliveryUnknownError(
                "Email delivery is unknown; do not retry automatically"
            ) from error
        return EmailWriteOutput(
            message_id=str(payload["id"]),
            thread_id=str(payload.get("threadId")) if payload.get("threadId") else None,
            status="sent",
        )

    def mark_read(self, message_id: str, read: bool) -> None:
        body = {"removeLabelIds": ["UNREAD"]} if read else {"addLabelIds": ["UNREAD"]}
        self._request("POST", f"/messages/{message_id}/modify", json=body)

    def close(self) -> None:
        self.client.close()

    def _request(self, method: str, path: str, **kwargs: object) -> dict[str, Any]:
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.TimeoutException as error:
            raise EmailTimeoutError("Gmail request timed out") from error
        except httpx.HTTPError as error:
            raise EmailTransientError("Gmail is unavailable") from error
        if response.status_code == 401:
            raise EmailAuthenticationError("Gmail authorization expired")
        if response.status_code == 403:
            raise EmailPermissionError("Gmail permission denied")
        if response.status_code == 404:
            raise EmailNotFoundError("Email resource was not found")
        if response.status_code == 429:
            raise EmailRateLimitError("Gmail rate limit exceeded")
        if response.status_code >= 500:
            raise EmailTransientError("Gmail is temporarily unavailable")
        if response.status_code >= 400:
            raise EmailValidationError("Gmail rejected the request")
        value = response.json()
        if not isinstance(value, dict):
            raise EmailValidationError("Gmail returned an invalid response")
        return value

    def _summary(self, value: dict[str, Any]) -> EmailMessageSummary:
        headers = _headers(value)
        return EmailMessageSummary(
            id=str(value["id"]),
            thread_id=str(value["threadId"]),
            subject=headers.get("subject", "(no subject)"),
            sender=_addresses(headers.get("from", ""), required=True)[0],
            recipients=_addresses(headers.get("to", "")),
            sent_at=_date(headers.get("date")),
            snippet=str(value.get("snippet", ""))[:500],
            unread="UNREAD" in value.get("labelIds", []),
            has_attachments=_has_attachments(value.get("payload", {})),
        )

    def _message(self, value: dict[str, Any]) -> EmailMessage:
        summary = self._summary(value)
        headers = _headers(value)
        body, attachments = _parts(value.get("payload", {}))
        if not body:
            body = _decode(value.get("payload", {}).get("body", {}).get("data", ""))
        maximum = self.max_body_chars
        safe_attachments = [self.policy.attachment(item) for item in attachments]
        return EmailMessage(
            **summary.model_dump(),
            cc=_addresses(headers.get("cc", "")),
            reply_to=_addresses(headers.get("reply-to", "")),
            text_body=body[:maximum],
            body_truncated=len(body) > maximum,
            attachments=safe_attachments,
            provider_headers={key: value for key in ("message-id",) if (value := headers.get(key))},
        )


def _headers(value: dict[str, Any]) -> dict[str, str]:
    return {
        str(item.get("name", "")).lower(): str(item.get("value", ""))
        for item in value.get("payload", {}).get("headers", [])
    }


def _addresses(value: str, *, required: bool = False) -> list[EmailAddress]:
    values = [
        EmailAddress(address=address, name=name or None)
        for name, address in getaddresses([value])
        if address
    ]
    return values or ([EmailAddress(address="unknown@example.com")] if required else [])


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def _decode(value: str) -> str:
    if not value:
        return ""
    try:
        padded = value + "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except (ValueError, TypeError):
        return ""


def _parts(payload: dict[str, Any]) -> tuple[str, list[EmailAttachmentMetadata]]:
    plain: list[str] = []
    html_parts: list[str] = []
    attachments: list[EmailAttachmentMetadata] = []
    for part in _walk(payload):
        body = part.get("body", {})
        filename = str(part.get("filename", ""))
        mime = str(part.get("mimeType", "application/octet-stream"))
        attachment_id = body.get("attachmentId")
        if filename or attachment_id:
            attachments.append(
                EmailAttachmentMetadata(
                    attachment_id=str(attachment_id) if attachment_id else None,
                    filename=filename or "attachment",
                    mime_type=mime,
                    size=int(body.get("size", 0)),
                )
            )
            continue
        data = _decode(str(body.get("data", "")))
        if mime == "text/plain":
            plain.append(data)
        elif mime == "text/html":
            parser = _TextExtractor()
            parser.feed(html.unescape(data))
            html_parts.append(parser.text())
    return ("\n\n".join(plain or html_parts).strip(), attachments)


def _walk(payload: dict[str, Any]) -> list[dict[str, Any]]:
    values = [payload]
    for part in payload.get("parts", []):
        values.extend(_walk(part))
    return values


def _has_attachments(payload: dict[str, Any]) -> bool:
    return any(
        bool(part.get("filename") or part.get("body", {}).get("attachmentId"))
        for part in _walk(payload)
    )
