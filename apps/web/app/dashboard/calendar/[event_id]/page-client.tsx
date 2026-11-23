'use client';

import type { CalendarEvent } from '@agent/shared';
import { useSearchParams } from 'next/navigation';
import { useParams } from '../../../../lib/route-params';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { getCalendarEvent } from '../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';
import { label } from '../../../../lib/labels';

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
      .catch(() => setError('Não foi possível ler este evento.'));
  }, [accountId, calendarId, params.event_id, user]);

  if (loading || !user)
    return <main className="loading-page">A carregar o evento…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Conteúdo externo não verificado</p>
          <h1>{event?.title ?? 'Evento de calendário'}</h1>
          <p>Estado: {event ? label(event.status) : 'A carregar'}</p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {event && (
        <section className="workflow-panel">
          <p>Start: {event.start.date_time ?? event.start.date}</p>
          <p>End: {event.end.date_time ?? event.end.date}</p>
          <p>Time zone: {event.start.time_zone ?? 'Todo o dia'}</p>
          <p>Location: {event.location || 'Não definido'}</p>
          <p>Description: {event.description || 'Não definido'}</p>
          <h2>Participantes</h2>
          {event.attendees.map((attendee) => (
            <p key={attendee.email}>
              {attendee.display_name || attendee.email} ·{' '}
              {attendee.response_status || 'Sem resposta'}
            </p>
          ))}
        </section>
      )}
    </main>
  );
}
