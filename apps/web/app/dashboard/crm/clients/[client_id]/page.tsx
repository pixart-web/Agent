'use client';

import type { CrmClient360 } from '@agent/shared';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ClientInsight } from '../../../../../components/client-insight';
import { DashboardNav } from '../../../../../components/dashboard-nav';
import { getCrmClient360 } from '../../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../../lib/use-authenticated-user';

function money(amountMinor: number, currency: string) {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
  }).format(amountMinor / 100);
}

export default function Client360Page() {
  const { user, loading } = useAuthenticatedUser();
  const { client_id: clientId } = useParams<{ client_id: string }>();
  const [view, setView] = useState<CrmClient360 | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    void getCrmClient360(clientId)
      .then(setView)
      .catch(() => setError('Unable to load this client.'));
  }, [clientId, user]);

  if (loading || !user)
    return <main className="loading-page">Loading client…</main>;

  const client = view?.client;
  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Client 360 · governed context</p>
          <h1>{client?.organization.name || 'Client'}</h1>
          <p>
            {client
              ? client.lifecycle_status +
                ' · ' +
                (client.industry || 'No industry')
              : 'Loading business context…'}
          </p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {view && (
        <>
          <section className="workflow-panel">
            <h2>Overview</h2>
            <p>{view.client.summary || 'No client summary.'}</p>
            <p>
              Owner: {view.client.owner_user_id} · CRM facts are separated from
              model-generated summaries.
            </p>
          </section>

          <section className="workflow-panel">
            <h2>Contacts</h2>
            <div className="agent-grid">
              {view.contacts.map((contact) => (
                <Link
                  className="agent-card agent-card--link"
                  href={'/dashboard/crm/contacts/' + contact.id}
                  key={contact.id}
                >
                  <p className="eyebrow">{contact.status}</p>
                  <h3>{contact.full_name}</h3>
                  <p>{contact.job_title || 'No job title'}</p>
                </Link>
              ))}
            </div>
            {view.contacts.length === 0 && (
              <p className="empty-state">No contacts.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Emails & meetings</h2>
            {[...view.emails, ...view.meetings].map((activity) => (
              <article className="agent-card" key={activity.id}>
                <p className="eyebrow">{activity.activity_type}</p>
                <h3>{activity.subject}</h3>
                <p>{new Date(activity.occurred_at).toLocaleString()}</p>
              </article>
            ))}
            {view.emails.length + view.meetings.length === 0 && (
              <p className="empty-state">
                No linked email or meeting references.
              </p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Projects</h2>
            <div className="agent-grid">
              {view.projects.map((project) => (
                <article className="agent-card" key={project.id}>
                  <p className="eyebrow">{project.status}</p>
                  <h3>{project.name}</h3>
                  <p>{project.description || 'No description'}</p>
                  <p>Due: {project.due_on || 'Not scheduled'}</p>
                </article>
              ))}
            </div>
            {view.projects.length === 0 && (
              <p className="empty-state">No projects.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Tasks</h2>
            {view.tasks.map((task) => (
              <article className="agent-card" key={task.id}>
                <p className="eyebrow">
                  {task.status} · {task.agent_id}
                </p>
                <h3>{task.title}</h3>
              </article>
            ))}
            {view.tasks.length === 0 && (
              <p className="empty-state">No linked tasks.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Opportunities</h2>
            <div className="agent-grid">
              {view.opportunities.map((opportunity) => (
                <article className="agent-card" key={opportunity.id}>
                  <p className="eyebrow">
                    {opportunity.status} · {opportunity.probability}%
                  </p>
                  <h3>{opportunity.title}</h3>
                  <p>{money(opportunity.amount_minor, opportunity.currency)}</p>
                </article>
              ))}
            </div>
            {view.opportunities.length === 0 && (
              <p className="empty-state">No opportunities.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Notes & activity</h2>
            {view.notes.map((note) => (
              <article className="agent-card" key={note.id}>
                <p className="eyebrow">Untrusted CRM note · {note.source}</p>
                <p>{note.body}</p>
              </article>
            ))}
            {view.activities.map((activity) => (
              <article className="agent-card" key={activity.id}>
                <p className="eyebrow">{activity.activity_type}</p>
                <p>{activity.subject}</p>
              </article>
            ))}
            {view.notes.length + view.activities.length === 0 && (
              <p className="empty-state">No notes or activity.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Kiko insights</h2>
            {view.insights.map((insight, index) => (
              <ClientInsight insight={insight} key={index} />
            ))}
            {view.insights.length === 0 && (
              <p className="empty-state">No insights available.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>History</h2>
            {view.history.map((item) => (
              <p key={item.id}>
                {item.entity_type} · {item.event_type} ·{' '}
                {new Date(item.created_at).toLocaleString()}
              </p>
            ))}
          </section>
        </>
      )}
    </main>
  );
}
