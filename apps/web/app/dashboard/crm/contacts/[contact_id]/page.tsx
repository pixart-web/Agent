'use client';

import type { CrmActivity, CrmContact } from '@agent/shared';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../../components/dashboard-nav';
import {
  getCrmContact,
  listCrmActivities,
} from '../../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../../lib/use-authenticated-user';

export default function CrmContactPage() {
  const { user, loading } = useAuthenticatedUser();
  const { contact_id: contactId } = useParams<{ contact_id: string }>();
  const [contact, setContact] = useState<CrmContact | null>(null);
  const [activities, setActivities] = useState<CrmActivity[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    void Promise.all([
      getCrmContact(contactId),
      listCrmActivities({ contactId }),
    ])
      .then(([contactValue, activityValue]) => {
        setContact(contactValue);
        setActivities(activityValue.activities);
      })
      .catch(() => setError('Unable to load this contact.'));
  }, [contactId, user]);

  if (loading || !user)
    return <main className="loading-page">Loading contact…</main>;
  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">CRM contact</p>
          <h1>{contact?.full_name || 'Contact'}</h1>
          <p>{contact?.job_title || 'No job title'}</p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {contact && (
        <section className="workflow-panel">
          <h2>Contact methods</h2>
          {contact.methods.map((method) => (
            <p key={method.id}>
              {method.method_type}: {method.value}{' '}
              {method.is_primary ? '· primary' : ''}
            </p>
          ))}
          <p>Website: {contact.website || 'None'}</p>
          <p>Tags: {contact.tags.join(', ') || 'None'}</p>
        </section>
      )}
      <section className="workflow-panel">
        <h2>Activity</h2>
        {activities.map((activity) => (
          <article className="agent-card" key={activity.id}>
            <p className="eyebrow">{activity.activity_type}</p>
            <h3>{activity.subject}</h3>
            <p>{new Date(activity.occurred_at).toLocaleString()}</p>
          </article>
        ))}
        {activities.length === 0 && (
          <p className="empty-state">No linked activity.</p>
        )}
      </section>
    </main>
  );
}
