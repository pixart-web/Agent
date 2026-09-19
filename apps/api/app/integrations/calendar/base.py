from dataclasses import dataclass
from typing import Protocol

from app.integrations.calendar.schemas import (
    CalendarAvailability,
    CalendarAvailabilityInput,
    CalendarCancelEventInput,
    CalendarCreateEventInput,
    CalendarEvent,
    CalendarInfo,
    CalendarUpdateEventInput,
    CalendarWriteOutput,
)


@dataclass(frozen=True)
class CalendarPage:
    calendars: list[CalendarInfo]
    next_page_token: str | None = None


@dataclass(frozen=True)
class CalendarEventPage:
    events: list[CalendarEvent]
    next_page_token: str | None = None


class CalendarProvider(Protocol):
    def list_calendars(self, limit: int, page_token: str | None = None) -> CalendarPage: ...
    def list_events(
        self,
        calendar_id: str,
        time_min,
        time_max,
        limit: int,
        page_token: str | None = None,
        query: str | None = None,
    ) -> CalendarEventPage: ...
    def get_event(self, calendar_id: str, event_id: str) -> CalendarEvent: ...
    def get_availability(self, value: CalendarAvailabilityInput) -> list[CalendarAvailability]: ...
    def create_event(
        self, value: CalendarCreateEventInput, idempotency_key: str
    ) -> CalendarWriteOutput: ...
    def update_event(
        self, value: CalendarUpdateEventInput, idempotency_key: str
    ) -> CalendarWriteOutput: ...
    def cancel_event(
        self, value: CalendarCancelEventInput, idempotency_key: str
    ) -> CalendarWriteOutput: ...
    def close(self) -> None: ...
