from pathlib import PurePath

from app.integrations.email.errors import EmailPermissionError, EmailValidationError
from app.integrations.email.schemas import EmailAddress, EmailAttachmentMetadata

_BLOCKED_EXTENSIONS = {
    ".app",
    ".bat",
    ".cmd",
    ".com",
    ".cpl",
    ".dll",
    ".dmg",
    ".exe",
    ".hta",
    ".jar",
    ".js",
    ".jse",
    ".lnk",
    ".msi",
    ".ps1",
    ".scr",
    ".vbe",
    ".vbs",
}


class DataClassificationPolicy:
    """Extension hook for DLP/classification without claiming perfect detection."""

    def inspect(self, _subject: str, _body: str) -> list[str]:
        return []


class EmailPolicy:
    def __init__(
        self,
        allowed_accounts: list[str],
        *,
        max_recipients: int,
        max_attachment_bytes: int,
        classifier: DataClassificationPolicy | None = None,
    ) -> None:
        self.allowed_accounts = set(allowed_accounts)
        self.max_recipients = max_recipients
        self.max_attachment_bytes = max_attachment_bytes
        self.classifier = classifier or DataClassificationPolicy()

    def authorize_account(self, address: str) -> str:
        normalized = address.strip().lower()
        if normalized not in self.allowed_accounts:
            raise EmailPermissionError("Email account is not allowlisted")
        return normalized

    def recipients(self, *groups: list[EmailAddress]) -> list[str]:
        values = [str(item.address).strip().lower() for group in groups for item in group]
        if not values or len(values) > self.max_recipients:
            raise EmailValidationError("Recipient count exceeds the configured policy")
        if len(values) != len(set(values)):
            raise EmailValidationError("Duplicate email recipients are not allowed")
        return values

    def classify(self, subject: str, body: str) -> list[str]:
        return self.classifier.inspect(subject, body)

    def attachment(self, value: EmailAttachmentMetadata) -> EmailAttachmentMetadata:
        extension = PurePath(value.filename).suffix.lower()
        blocked = extension in _BLOCKED_EXTENSIONS or value.size > self.max_attachment_bytes
        return value.model_copy(update={"blocked": blocked})
