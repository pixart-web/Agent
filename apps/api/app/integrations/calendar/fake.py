from copy import deepcopy
from datetime import datetime
from uuid import uuid4

from app.integrations.calendar.base import CalendarEventPage, CalendarPage
from app.integrations.calendar.errors import (
    CalendarDeliveryUnknownError,
    CalendarNotFoundError,
)
from app.integrations.calendar.schemas import (
    CalendarAvailability,
    CalendarAvailabilityInput,
    CalendarBusyPeriod,
    CalendarCancelEventInput,
    CalendarCreateEventInput,
    CalendarEvent,
    CalendarInfo,
    CalendarUpdateEventInput,
    CalendarWriteOutput,
)


class FakeCalendarProvider:
    def __init__(
        self,
        calendars: list[CalendarInfo] | None = None,
        events: list[CalendarEvent] | None = None,
        *,
        delivery_unknown: bool = False,
    ) -> None:
        self.calendars = calendars or []
        self.events = {event.id: deepcopy(event) for event in events or []}
        self.delivery_unknown = delivery_unknown
        self.write_count = 0

    def list_calendars(self, limit: int, page_token: str | None = None) -> CalendarPage:
        return CalendarPage(self.calendars[:limit])

    def list_events(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
        limit: int,
        page_token: str | None = None,
        query: str | None = None,
    ) -> CalendarEventPage:
        values = [event for event in self.events.values() if event.calendar_id == calendar_id]
        if query:
            needle = query.lower()
            values = [
                event
                for event in values
                if needle in event.title.lower() or needle in event.description.lower()
            ]
        return CalendarEventPage(values[:limit])

    def get_event(self, calendar_id: str, event_id: str) -> CalendarEvent:
        event = self.events.get(event_id)
        if event is None or event.calendar_id != calendar_id:
            raise CalendarNotFoundError("Calendar event was not found")
        return deepcopy(event)

    def get_availability(self, value: CalendarAvailabilityInput) -> list[CalendarAvailability]:
        output = []
        for calendar_id in value.calendar_ids:
            busy = []
            for event in self.events.values():
                if event.calendar_id != calendar_id or event.start.date_time is None:
                    continue
                if event.end.date_time > value.time_min and event.start.date_time < value.time_max:
                    busy.append(
                        CalendarBusyPeriod(start=event.start.date_time, end=event.end.date_time)
                    )
            output.append(CalendarAvailability(calendar_id=calendar_id, busy=busy))
        return output

    def create_event(
        self, value: CalendarCreateEventInput, idempotency_key: str
    ) -> CalendarWriteOutput:
        self._before_write()
        event_id = f"fake-{uuid4()}"
        self.events[event_id] = CalendarEvent(
            id=event_id,
            calendar_id=value.calendar_id,
            title=value.title,
            description=value.description,
            location=value.location,
            start=value.start,
            end=value.end,
            status="confirmed",
            attendees=[{"email": attendee, "external": True} for attendee in value.attendees],
            recurrence=value.recurrence,
        )
        return CalendarWriteOutput(
            event_id=event_id, calendar_id=value.calendar_id, status="confirmed"
        )

    def update_event(
        self, value: CalendarUpdateEventInput, idempotency_key: str
    ) -> CalendarWriteOutput:
        self._before_write()
        current = self.get_event(value.calendar_id, value.event_id)
        self.events[value.event_id] = current.model_copy(
            update={
                "title": value.title,
                "description": value.description,
                "location": value.location,
                "start": value.start,
                "end": value.end,
                "recurrence": value.recurrence,
            }
        )
        return CalendarWriteOutput(
            event_id=value.event_id, calendar_id=value.calendar_id, status="confirmed"
        )

    def cancel_event(
        self, value: CalendarCancelEventInput, idempotency_key: str
    ) -> CalendarWriteOutput:
        self._before_write()
        current = self.get_event(value.calendar_id, value.event_id)
        self.events[value.event_id] = current.model_copy(update={"status": "cancelled"})
        return CalendarWriteOutput(
            event_id=value.event_id, calendar_id=value.calendar_id, status="cancelled"
        )

    def _before_write(self) -> None:
        self.write_count += 1
        if self.delivery_unknown:
            raise CalendarDeliveryUnknownError("Calendar provider outcome is unknown")

    def close(self) -> None:
        return None
