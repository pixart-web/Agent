import argparse
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.config import get_settings
from app.integrations.calendar.oauth import GoogleCalendarOAuthClient
from app.integrations.calendar.policy import CalendarPolicy
from app.integrations.calendar.providers.google import GoogleCalendarProvider
from app.integrations.calendar.schemas import CalendarCreateEventInput, CalendarEventTime


def main() -> None:
    parser = argparse.ArgumentParser(description="Operator-gated Google Calendar smoke test")
    parser.add_argument("--allow-create", action="store_true")
    parser.add_argument("--calendar-id", default="primary")
    args = parser.parse_args()
    settings = get_settings()
    if not settings.calendar_integration_enabled:
        raise SystemExit("CALENDAR_INTEGRATION_ENABLED must be true")
    refresh_token = os.environ.get("CALENDAR_SMOKE_REFRESH_TOKEN")
    if not refresh_token:
        raise SystemExit("CALENDAR_SMOKE_REFRESH_TOKEN is required at runtime")
    if args.allow_create and not settings.calendar_write_enabled:
        raise SystemExit("CALENDAR_WRITE_ENABLED must be true for the explicit write smoke test")

    access_token = GoogleCalendarOAuthClient(settings).refresh(refresh_token)
    policy = CalendarPolicy(
        settings.calendar_allowed_account_list,
        settings.calendar_internal_domain_list,
        settings.calendar_max_attendees,
    )
    provider = GoogleCalendarProvider(access_token, settings.calendar_api_timeout_seconds, policy)
    try:
        calendars = provider.list_calendars(10).calendars
        primary = next((item for item in calendars if item.primary), None)
        if primary is None:
            raise SystemExit("read smoke failed: no primary calendar returned")
        policy.authorize_account(primary.id)
        now = datetime.now(UTC).replace(second=0, microsecond=0) + timedelta(days=7)
        events = provider.list_events(args.calendar_id, now, now + timedelta(days=1), 1)
        print(
            f"read smoke passed for {primary.id}; calendars={len(calendars)}; "
            f"events={len(events.events)}"
        )
        if args.allow_create:
            value = CalendarCreateEventInput(
                account_id=uuid4(),
                calendar_id=args.calendar_id,
                title="Kiko Calendar integration smoke test",
                description="Explicit operator-authorized smoke test.",
                start=CalendarEventTime(date_time=now, time_zone="UTC"),
                end=CalendarEventTime(date_time=now + timedelta(minutes=15), time_zone="UTC"),
            )
            result = provider.create_event(value, f"operator-smoke-{uuid4()}")
            print(f"create smoke passed; event_id={result.event_id}")
    finally:
        provider.close()


if __name__ == "__main__":
    main()
