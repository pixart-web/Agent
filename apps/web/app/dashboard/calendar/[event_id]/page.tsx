'use client';

import type { CalendarEvent } from '@agent/shared';
import { useParams, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { getCalendarEvent } from '../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';

export default function CalendarEventPage() {
  const { user, loading } = useAuthenticatedUser();
  const params = useParams<{ event_id: string }>();
  const search = useSearchParams();
  const [event, setEvent] = useState<CalendarEvent | null>(null);
  const [error, setError] = useState('');
  const accountId = search.get('account') ?? '';
  const calendarId = search.get('calendar') ?? '';

  useEffect(() => {
    if (!user || !accountId || !calendarId) return;
    void getCalendarEvent(accountId, calendarId, params.event_id)
      .then((value) => setEvent(value.event))
      .catch(() => setError('Unable to read this event.'));
  }, [accountId, calendarId, params.event_id, user]);

  if (loading || !user)
    return <main className="loading-page">Loading event…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Untrusted external content</p>
          <h1>{event?.title ?? 'Calendar event'}</h1>
          <p>Status: {event?.status ?? 'Loading'}</p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {event && (
        <section className="workflow-panel">
          <p>Start: {event.start.date_time ?? event.start.date}</p>
          <p>End: {event.end.date_time ?? event.end.date}</p>
          <p>Time zone: {event.start.time_zone ?? 'All day'}</p>
          <p>Location: {event.location || 'Not set'}</p>
          <p>Description: {event.description || 'Not set'}</p>
          <h2>Attendees</h2>
          {event.attendees.map((attendee) => (
            <p key={attendee.email}>
              {attendee.display_name || attendee.email} ·{' '}
              {attendee.response_status || 'No response'}
            </p>
          ))}
        </section>
      )}
    </main>
  );
}
