from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.integrations.calendar.errors import (
    CalendarPermissionError,
    CalendarValidationError,
)


class CalendarPolicy:
    def __init__(
        self,
        allowed_accounts: list[str],
        internal_domains: list[str],
        max_attendees: int,
    ) -> None:
        self.allowed_accounts = {value.lower() for value in allowed_accounts}
        self.internal_domains = {value.lower() for value in internal_domains}
        self.max_attendees = max_attendees

    def authorize_account(self, address: str) -> str:
        normalized = address.strip().lower()
        if not normalized or normalized not in self.allowed_accounts:
            raise CalendarPermissionError("Calendar account is not allowed")
        return normalized

    def attendees(self, values: list[str]) -> tuple[list[str], list[str]]:
        normalized = [value.strip().lower() for value in values]
        if len(normalized) > self.max_attendees:
            raise CalendarValidationError("Calendar attendee limit exceeded")
        external = [
            value for value in normalized if value.rsplit("@", 1)[-1] not in self.internal_domains
        ]
        return normalized, external

    @staticmethod
    def time_zone(value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise CalendarValidationError("Unknown IANA time zone") from error
        return value
