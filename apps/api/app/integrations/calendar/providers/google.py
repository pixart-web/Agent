from datetime import date, datetime
from hashlib import sha256
from urllib.parse import quote

import httpx

from app.integrations.calendar.base import CalendarEventPage, CalendarPage
from app.integrations.calendar.errors import (
    CalendarAuthenticationError,
    CalendarDeliveryUnknownError,
    CalendarNotFoundError,
    CalendarPermissionError,
    CalendarRateLimitError,
    CalendarTimeoutError,
    CalendarTransientError,
    CalendarValidationError,
)
from app.integrations.calendar.policy import CalendarPolicy
from app.integrations.calendar.schemas import (
    CalendarAttendee,
    CalendarAvailability,
    CalendarAvailabilityInput,
    CalendarBusyPeriod,
    CalendarCancelEventInput,
    CalendarCreateEventInput,
    CalendarEvent,
    CalendarEventTime,
    CalendarInfo,
    CalendarUpdateEventInput,
    CalendarWriteOutput,
)

API_URL = "https://www.googleapis.com/calendar/v3"


class GoogleCalendarProvider:
    def __init__(self, access_token: str, timeout_seconds: float, policy: CalendarPolicy) -> None:
        self.client = httpx.Client(
            base_url=API_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=timeout_seconds,
            follow_redirects=False,
        )
        self.policy = policy

    def list_calendars(self, limit: int, page_token: str | None = None) -> CalendarPage:
        params: dict[str, object] = {"maxResults": limit, "showDeleted": False}
        if page_token:
            params["pageToken"] = page_token
        payload = self._request("GET", "/users/me/calendarList", params=params)
        return CalendarPage(
            calendars=[self._calendar(item) for item in self._items(payload)],
            next_page_token=self._string(payload.get("nextPageToken")),
        )

    def list_events(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
        limit: int,
        page_token: str | None = None,
        query: str | None = None,
    ) -> CalendarEventPage:
        params: dict[str, object] = {
            "maxResults": limit,
            "singleEvents": True,
            "orderBy": "startTime",
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "showDeleted": False,
        }
        if page_token:
            params["pageToken"] = page_token
        if query:
            params["q"] = query
        payload = self._request(
            "GET", f"/calendars/{quote(calendar_id, safe='')}/events", params=params
        )
        return CalendarEventPage(
            events=[self._event(item, calendar_id) for item in self._items(payload)],
            next_page_token=self._string(payload.get("nextPageToken")),
        )

    def get_event(self, calendar_id: str, event_id: str) -> CalendarEvent:
        payload = self._request(
            "GET",
            f"/calendars/{quote(calendar_id, safe='')}/events/{quote(event_id, safe='')}",
        )
        return self._event(payload, calendar_id)

    def get_availability(self, value: CalendarAvailabilityInput) -> list[CalendarAvailability]:
        payload = self._request(
            "POST",
            "/freeBusy",
            json={
                "timeMin": value.time_min.isoformat(),
                "timeMax": value.time_max.isoformat(),
                "timeZone": value.time_zone,
                "items": [{"id": item} for item in value.calendar_ids],
            },
        )
        calendars = payload.get("calendars")
        if not isinstance(calendars, dict):
            raise CalendarTransientError("Google Calendar availability response is invalid")
        output = []
        for calendar_id in value.calendar_ids:
            item = calendars.get(calendar_id, {})
            periods = item.get("busy", []) if isinstance(item, dict) else []
            busy = []
            for period in periods if isinstance(periods, list) else []:
                if not isinstance(period, dict):
                    continue
                start = self._parse_datetime(period.get("start"))
                end = self._parse_datetime(period.get("end"))
                if start and end:
                    busy.append(CalendarBusyPeriod(start=start, end=end))
            output.append(CalendarAvailability(calendar_id=calendar_id, busy=busy))
        return output

    def create_event(
        self, value: CalendarCreateEventInput, idempotency_key: str
    ) -> CalendarWriteOutput:
        existing = self._find_idempotent(value.calendar_id, idempotency_key)
        if existing is not None:
            return self._write_output(existing, value.calendar_id)
        body = self._event_body(value, idempotency_key)
        params = self._write_params(bool(value.attendees), value.add_conference)
        payload = self._request(
            "POST",
            f"/calendars/{quote(value.calendar_id, safe='')}/events",
            params=params,
            json=body,
            ambiguous_write=True,
        )
        return self._write_output(payload, value.calendar_id)

    def update_event(
        self, value: CalendarUpdateEventInput, idempotency_key: str
    ) -> CalendarWriteOutput:
        body = self._event_body(value, idempotency_key)
        params = self._write_params(bool(value.attendees), value.add_conference)
        payload = self._request(
            "PATCH",
            (
                f"/calendars/{quote(value.calendar_id, safe='')}/events/"
                f"{quote(value.event_id, safe='')}"
            ),
            params=params,
            json=body,
            ambiguous_write=True,
        )
        return self._write_output(payload, value.calendar_id)

    def cancel_event(
        self, value: CalendarCancelEventInput, idempotency_key: str
    ) -> CalendarWriteOutput:
        self._request(
            "DELETE",
            (
                f"/calendars/{quote(value.calendar_id, safe='')}/events/"
                f"{quote(value.event_id, safe='')}"
            ),
            params={"sendUpdates": "all" if value.notify_attendees else "none"},
            ambiguous_write=True,
        )
        return CalendarWriteOutput(
            event_id=value.event_id,
            calendar_id=value.calendar_id,
            status="cancelled",
        )

    def _find_idempotent(self, calendar_id: str, idempotency_key: str) -> dict[str, object] | None:
        payload = self._request(
            "GET",
            f"/calendars/{quote(calendar_id, safe='')}/events",
            params={
                "privateExtendedProperty": f"kiko_action={idempotency_key}",
                "maxResults": 1,
                "showDeleted": False,
            },
        )
        items = self._items(payload)
        return items[0] if items else None

    def _event_body(self, value, idempotency_key: str) -> dict[str, object]:
        attendees, _external = self.policy.attendees([str(item) for item in value.attendees])
        body: dict[str, object] = {
            "summary": value.title,
            "description": value.description,
            "location": value.location,
            "start": self._time_body(value.start),
            "end": self._time_body(value.end),
            "attendees": [{"email": item} for item in attendees],
            "recurrence": value.recurrence,
            "extendedProperties": {"private": {"kiko_action": idempotency_key}},
        }
        if value.add_conference:
            request_id = sha256(idempotency_key.encode()).hexdigest()[:32]
            body["conferenceData"] = {
                "createRequest": {
                    "requestId": request_id,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
        return body

    @staticmethod
    def _time_body(value: CalendarEventTime) -> dict[str, str]:
        if value.date is not None:
            return {"date": value.date.isoformat()}
        return {
            "dateTime": value.date_time.isoformat(),
            "timeZone": value.time_zone,
        }

    @staticmethod
    def _write_params(has_attendees: bool, conference: bool) -> dict[str, object]:
        params: dict[str, object] = {"sendUpdates": "all" if has_attendees else "none"}
        if conference:
            params["conferenceDataVersion"] = 1
        return params

    def _calendar(self, payload: dict[str, object]) -> CalendarInfo:
        return CalendarInfo(
            id=str(payload.get("id", "")),
            summary=str(payload.get("summary", "")),
            description=str(payload.get("description", "")),
            time_zone=str(payload.get("timeZone", "UTC")),
            primary=bool(payload.get("primary", False)),
            access_role=str(payload.get("accessRole", "reader")),
        )

    def _event(self, payload: dict[str, object], calendar_id: str) -> CalendarEvent:
        attendees_payload = payload.get("attendees", [])
        attendees = []
        if isinstance(attendees_payload, list):
            for item in attendees_payload:
                if not isinstance(item, dict) or not item.get("email"):
                    continue
                email = str(item["email"])
                _all, external = self.policy.attendees([email])
                attendees.append(
                    CalendarAttendee(
                        email=email,
                        display_name=self._string(item.get("displayName")),
                        response_status=self._string(item.get("responseStatus")),
                        optional=bool(item.get("optional", False)),
                        external=bool(external),
                    )
                )
        recurrence = payload.get("recurrence", [])
        organizer = payload.get("organizer", {})
        conference = payload.get("conferenceData", {})
        conference_url = self._string(payload.get("hangoutLink"))
        if not conference_url and isinstance(conference, dict):
            entries = conference.get("entryPoints", [])
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict) and entry.get("entryPointType") == "video":
                        conference_url = self._string(entry.get("uri"))
                        break
        return CalendarEvent(
            id=str(payload.get("id", "")),
            calendar_id=calendar_id,
            title=str(payload.get("summary", "(untitled event)")),
            description=str(payload.get("description", "")),
            location=str(payload.get("location", "")),
            start=self._event_time(payload.get("start")),
            end=self._event_time(payload.get("end")),
            status=str(payload.get("status", "confirmed")),
            attendees=attendees,
            recurrence=[str(item) for item in recurrence] if isinstance(recurrence, list) else [],
            conference_url=conference_url,
            html_link=self._string(payload.get("htmlLink")),
            organizer_email=(
                self._string(organizer.get("email")) if isinstance(organizer, dict) else None
            ),
            updated_at=self._parse_datetime(payload.get("updated")),
        )

    @staticmethod
    def _event_time(value: object) -> CalendarEventTime:
        if not isinstance(value, dict):
            raise CalendarTransientError("Google Calendar event time is invalid")
        if value.get("date"):
            return CalendarEventTime(
                date=date.fromisoformat(str(value["date"])),
                time_zone=GoogleCalendarProvider._string(value.get("timeZone")),
            )
        parsed = GoogleCalendarProvider._parse_datetime(value.get("dateTime"))
        if parsed is None:
            raise CalendarTransientError("Google Calendar event time is invalid")
        return CalendarEventTime(
            date_time=parsed,
            time_zone=GoogleCalendarProvider._string(value.get("timeZone")),
        )

    @staticmethod
    def _write_output(payload: dict[str, object], calendar_id: str) -> CalendarWriteOutput:
        return CalendarWriteOutput(
            event_id=str(payload.get("id", "")),
            calendar_id=calendar_id,
            status=str(payload.get("status", "confirmed")),
            html_link=GoogleCalendarProvider._string(payload.get("htmlLink")),
        )

    @staticmethod
    def _items(payload: dict[str, object]) -> list[dict[str, object]]:
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise CalendarTransientError("Google Calendar response is invalid")
        return [item for item in items if isinstance(item, dict)]

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise CalendarTransientError("Google Calendar timestamp is invalid") from error

    @staticmethod
    def _string(value: object) -> str | None:
        return value if isinstance(value, str) else None

    def _request(
        self,
        method: str,
        path: str,
        *,
        ambiguous_write: bool = False,
        **kwargs: object,
    ) -> dict[str, object]:
        try:
            response = self.client.request(method, path, **kwargs)
        except httpx.TimeoutException as error:
            if ambiguous_write:
                raise CalendarDeliveryUnknownError(
                    "Calendar provider outcome is unknown"
                ) from error
            raise CalendarTimeoutError("Google Calendar request timed out") from error
        except httpx.HTTPError as error:
            if ambiguous_write:
                raise CalendarDeliveryUnknownError(
                    "Calendar provider outcome is unknown"
                ) from error
            raise CalendarTransientError("Google Calendar is unavailable") from error
        if response.status_code in {401, 403}:
            error_type = (
                CalendarAuthenticationError
                if response.status_code == 401
                else CalendarPermissionError
            )
            raise error_type("Google Calendar authorization failed")
        if response.status_code == 404:
            raise CalendarNotFoundError("Calendar resource was not found")
        if response.status_code == 429:
            raise CalendarRateLimitError("Google Calendar rate limit exceeded")
        if response.status_code >= 500:
            raise CalendarTransientError("Google Calendar service failed")
        if response.status_code >= 400:
            raise CalendarValidationError("Google Calendar rejected the request")
        if response.status_code == 204 or not response.content:
            return {}
        payload = response.json()
        if not isinstance(payload, dict):
            raise CalendarTransientError("Google Calendar response is invalid")
        return payload

    def close(self) -> None:
        self.client.close()
