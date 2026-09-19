'use client';

import type {
  CalendarAccount,
  CalendarEvent,
  CalendarInfo,
} from '@agent/shared';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  listCalendarAccounts,
  listCalendarEvents,
  listCalendars,
} from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function CalendarPage() {
  const { user, loading } = useAuthenticatedUser();
  const [accounts, setAccounts] = useState<CalendarAccount[]>([]);
  const [accountId, setAccountId] = useState('');
  const [calendars, setCalendars] = useState<CalendarInfo[]>([]);
  const [calendarId, setCalendarId] = useState('');
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    void listCalendarAccounts().then((values) => {
      const connected = values.filter((value) => value.status === 'connected');
      setAccounts(connected);
      if (connected[0]) setAccountId(connected[0].id);
    });
  }, [user]);

  useEffect(() => {
    if (!accountId) return;
    void listCalendars(accountId)
      .then((value) => {
        setCalendars(value.calendars);
        const selected =
          value.calendars.find((item) => item.primary) ?? value.calendars[0];
        setCalendarId(selected?.id ?? '');
      })
      .catch(() => setError('Unable to read calendars.'));
  }, [accountId]);

  useEffect(() => {
    if (!accountId || !calendarId) return;
    const start = new Date();
    const end = new Date(start);
    end.setDate(end.getDate() + 30);
    void listCalendarEvents(
      accountId,
      calendarId,
      start.toISOString(),
      end.toISOString(),
    )
      .then((value) => setEvents(value.events))
      .catch(() => setError('Unable to read events.'));
  }, [accountId, calendarId]);

  if (loading || !user)
    return <main className="loading-page">Loading Calendar…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Untrusted external content</p>
          <h1>Calendar</h1>
          <p>
            Upcoming events are read on demand. Changes require an explicit
            approval.
          </p>
        </div>
        <div>
          <select
            value={accountId}
            onChange={(event) => setAccountId(event.target.value)}
          >
            {accounts.map((account) => (
              <option value={account.id} key={account.id}>
                {account.email_address}
              </option>
            ))}
          </select>
          <select
            value={calendarId}
            onChange={(event) => setCalendarId(event.target.value)}
          >
            {calendars.map((calendar) => (
              <option value={calendar.id} key={calendar.id}>
                {calendar.summary}
              </option>
            ))}
          </select>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <section className="workflow-panel">
        {events.map((event) => (
          <Link
            className="agent-card agent-card--link"
            href={
              '/dashboard/calendar/' +
              encodeURIComponent(event.id) +
              '?account=' +
              encodeURIComponent(accountId) +
              '&calendar=' +
              encodeURIComponent(calendarId)
            }
            key={event.id}
          >
            <p className="eyebrow">{event.status}</p>
            <h3>{event.title}</h3>
            <p>
              {event.start.date_time ?? event.start.date} →{' '}
              {event.end.date_time ?? event.end.date}
            </p>
            <p>{event.location}</p>
          </Link>
        ))}
        {events.length === 0 && (
          <p className="empty-state">No events in the next 30 days.</p>
        )}
      </section>
    </main>
  );
}
