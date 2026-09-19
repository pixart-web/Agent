# Calendar integration

Phase 5C adds a provider-neutral Calendar boundary:

```text
CalendarTool v1 -> CalendarService -> CalendarProvider -> GoogleCalendarProvider
```

The first provider is Google Calendar. Agent and browser payloads never contain OAuth tokens.
Refresh tokens are encrypted with the existing integration secret store and are resolved only
inside backend execution. OAuth state uses the persisted, signed, expiring, user-bound and
one-shot nonce introduced for Email.

## Capabilities and governance

Reads are green actions: list calendars/events, search, event detail and free/busy availability.
Event titles, descriptions, locations, attendees and provider links are explicitly marked as
untrusted external content. React renders these values as text; agents are instructed never to
follow embedded instructions.

Create, update and cancel are yellow actions with zero automatic retries. Approval previews
show the account, calendar, event identifier, title, complete start/end and IANA time zone,
location, attendees, external attendees, recurrence, conference and notification settings.
The execution worker verifies the exact approved payload fingerprint.

Before a provider write, CalendarService locks the TaskAction and reserves one
CalendarWriteRecord keyed by the action and fingerprint. Concurrent workers therefore cannot
both call the provider. A successful repeat returns the stored result; pending, failed or
ambiguous delivery records prohibit blind retry. Ambiguous network outcomes are persisted as
`delivery_unknown` for human reconciliation.

## Time and event semantics

Timed events require offset-aware timestamps plus explicit IANA time zones. All-day events use
exclusive end dates. The schemas preserve recurrence rules and DST-relevant zone identifiers.
Google Meet creation is optional and deterministic per approved action. Attendee notifications
are explicit.

## Persistence

Migration `20260919_0010` adds `calendar_write_records` and `calendar_references`. It follows
`20260823_0009` and has a complete downgrade. IntegrationAccount remains provider-neutral and
queries are provider-filtered so a Gmail account cannot be used by Calendar or vice versa.

## Configuration

Calendar is disabled by default. Configure Google client credentials, the Calendar redirect
URI, encryption key and an explicit account allowlist. Keep `CALENDAR_WRITE_ENABLED=false`
until write access is intentionally enabled. Never commit real client secrets, refresh tokens
or Fernet keys.

CI and local tests use FakeCalendarProvider; they do not contact Google or create real events.
