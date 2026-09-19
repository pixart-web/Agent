from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CalendarEventTime(StrictModel):
    date_time: datetime | None = None
    date: Date | None = None
    time_zone: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_value(self) -> CalendarEventTime:
        if (self.date_time is None) == (self.date is None):
            raise ValueError("Exactly one of date_time or date is required")
        if self.date_time is not None and self.date_time.utcoffset() is None:
            raise ValueError("Timed events require an offset-aware date_time")
        if self.time_zone:
            try:
                ZoneInfo(self.time_zone)
            except ZoneInfoNotFoundError as error:
                raise ValueError("Unknown IANA time zone") from error
        return self


class CalendarInfo(StrictModel):
    id: str
    summary: str
    description: str = ""
    time_zone: str
    primary: bool = False
    access_role: str
    external_content: bool = True
    trust: Literal["untrusted"] = "untrusted"


class CalendarAttendee(StrictModel):
    email: EmailStr
    display_name: str | None = Field(default=None, max_length=200)
    response_status: str | None = Field(default=None, max_length=64)
    optional: bool = False
    external: bool = False


class CalendarEvent(StrictModel):
    id: str
    calendar_id: str
    title: str
    description: str = ""
    location: str = ""
    start: CalendarEventTime
    end: CalendarEventTime
    status: str
    attendees: list[CalendarAttendee] = Field(default_factory=list)
    recurrence: list[str] = Field(default_factory=list)
    conference_url: str | None = None
    html_link: str | None = None
    organizer_email: EmailStr | None = None
    updated_at: datetime | None = None
    external_content: bool = True
    trust: Literal["untrusted"] = "untrusted"


class CalendarListInput(StrictModel):
    account_id: UUID
    limit: int = Field(default=50, ge=1, le=250)
    page_token: str | None = Field(default=None, max_length=2000)


class CalendarEventsInput(CalendarListInput):
    calendar_id: str = Field(min_length=1, max_length=1024)
    time_min: datetime
    time_max: datetime

    @model_validator(mode="after")
    def validate_window(self) -> CalendarEventsInput:
        if self.time_min.utcoffset() is None or self.time_max.utcoffset() is None:
            raise ValueError("Event windows require offset-aware timestamps")
        if self.time_max <= self.time_min:
            raise ValueError("time_max must be after time_min")
        return self


class CalendarSearchInput(CalendarEventsInput):
    query: str = Field(min_length=1, max_length=500)


class CalendarEventInput(StrictModel):
    account_id: UUID
    calendar_id: str = Field(min_length=1, max_length=1024)
    event_id: str = Field(min_length=1, max_length=1024)


class CalendarAvailabilityInput(StrictModel):
    account_id: UUID
    calendar_ids: list[str] = Field(min_length=1, max_length=50)
    time_min: datetime
    time_max: datetime
    time_zone: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_window(self) -> CalendarAvailabilityInput:
        if self.time_min.utcoffset() is None or self.time_max.utcoffset() is None:
            raise ValueError("Availability requires offset-aware timestamps")
        if self.time_max <= self.time_min:
            raise ValueError("time_max must be after time_min")
        try:
            ZoneInfo(self.time_zone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Unknown IANA time zone") from error
        return self


class CalendarEventWriteBase(StrictModel):
    account_id: UUID
    calendar_id: str = Field(min_length=1, max_length=1024)
    title: str = Field(min_length=1, max_length=500)
    start: CalendarEventTime
    end: CalendarEventTime
    description: str = Field(default="", max_length=50_000)
    location: str = Field(default="", max_length=1000)
    attendees: list[EmailStr] = Field(default_factory=list, max_length=500)
    recurrence: list[str] = Field(default_factory=list, max_length=20)
    add_conference: bool = False

    @model_validator(mode="after")
    def validate_event(self) -> CalendarEventWriteBase:
        if (self.start.date is None) != (self.end.date is None):
            raise ValueError("Start and end must both be all-day or timed")
        if self.start.date is not None:
            if self.end.date <= self.start.date:
                raise ValueError("All-day event end date must be after start date")
        else:
            if not self.start.time_zone or not self.end.time_zone:
                raise ValueError("Timed event start and end require explicit IANA time zones")
            if self.end.date_time <= self.start.date_time:
                raise ValueError("Event end must be after start")
        if len(set(self.attendees)) != len(self.attendees):
            raise ValueError("Attendees must be unique")
        if any(not value.startswith(("RRULE:", "RDATE:", "EXDATE:")) for value in self.recurrence):
            raise ValueError("Recurrence entries must use RRULE, RDATE, or EXDATE")
        return self


class CalendarCreateEventInput(CalendarEventWriteBase):
    pass


class CalendarUpdateEventInput(CalendarEventWriteBase):
    event_id: str = Field(min_length=1, max_length=1024)


class CalendarCancelEventInput(StrictModel):
    account_id: UUID
    calendar_id: str = Field(min_length=1, max_length=1024)
    event_id: str = Field(min_length=1, max_length=1024)
    notify_attendees: bool = True


class CalendarBusyPeriod(StrictModel):
    start: datetime
    end: datetime


class CalendarAvailability(StrictModel):
    calendar_id: str
    busy: list[CalendarBusyPeriod]


class CalendarListOutput(StrictModel):
    calendars: list[CalendarInfo]
    next_page_token: str | None = None


class CalendarEventsOutput(StrictModel):
    events: list[CalendarEvent]
    next_page_token: str | None = None


class CalendarEventOutput(StrictModel):
    event: CalendarEvent


class CalendarAvailabilityOutput(StrictModel):
    calendars: list[CalendarAvailability]


class CalendarWriteOutput(StrictModel):
    event_id: str
    calendar_id: str
    status: str
    html_link: str | None = None
