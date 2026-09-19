'use client';

import type { CrmActivity, CrmOrganization } from '@agent/shared';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../../components/dashboard-nav';
import {
  getCrmOrganization,
  listCrmActivities,
} from '../../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../../lib/use-authenticated-user';

export default function CrmOrganizationPage() {
  const { user, loading } = useAuthenticatedUser();
  const { organization_id: organizationId } = useParams<{
    organization_id: string;
  }>();
  const [organization, setOrganization] = useState<CrmOrganization | null>(
    null,
  );
  const [activities, setActivities] = useState<CrmActivity[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    void Promise.all([
      getCrmOrganization(organizationId),
      listCrmActivities({ organizationId }),
    ])
      .then(([organizationValue, activityValue]) => {
        setOrganization(organizationValue);
        setActivities(activityValue.activities);
      })
      .catch(() => setError('Unable to load this organization.'));
  }, [organizationId, user]);

  if (loading || !user)
    return <main className="loading-page">Loading organization…</main>;
  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">CRM organization</p>
          <h1>{organization?.name || 'Organization'}</h1>
          <p>{organization?.member_count ?? 0} contacts</p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {organization && (
        <section className="workflow-panel">
          <p>Status: {organization.status}</p>
          <p>Website: {organization.website || 'Not set'}</p>
          <p>Tags: {organization.tags.join(', ') || 'None'}</p>
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
