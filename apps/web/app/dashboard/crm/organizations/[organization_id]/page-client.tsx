'use client';

import type { CrmActivity, CrmOrganization } from '@agent/shared';
import { useParams } from '../../../../../lib/route-params';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../../components/dashboard-nav';
import {
  getCrmOrganization,
  listCrmActivities,
  updateCrmOrganization,
} from '../../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../../lib/use-authenticated-user';
import { label } from '../../../../../lib/labels';

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
      .catch(() => setError('Não foi possível carregar esta organização.'));
  }, [organizationId, user]);

  if (loading || !user)
    return <main className="loading-page">A carregar a organização…</main>;
  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Organização do CRM</p>
          <h1>{organization?.name || 'Organização'}</h1>
          <p>{organization?.member_count ?? 0} contactos</p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {organization && (
        <section className="workflow-panel">
          <label>
            Ciclo de vida
            <select
              value={organization.status}
              onChange={async (event) => {
                try {
                  setOrganization(
                    await updateCrmOrganization(organization.id, {
                      status: event.target.value,
                    }),
                  );
                } catch {
                  setError('Não foi possível atualizar esta organização.');
                }
              }}
            >
              <option value="active">Ativo</option>
              <option value="inactive">Inativo</option>
              <option value="archived">Arquivado</option>
            </select>
          </label>
          <p>Estado: {label(organization.status)}</p>
          <p>Website: {organization.website || 'Não definido'}</p>
          <p>Tags: {organization.tags.join(', ') || 'Nenhum'}</p>
        </section>
      )}
      <section className="workflow-panel">
        <h2>Atividade</h2>
        {activities.map((activity) => (
          <article className="agent-card" key={activity.id}>
            <p className="eyebrow">{activity.activity_type}</p>
            <h3>{activity.subject}</h3>
            <p>{new Date(activity.occurred_at).toLocaleString('pt-PT')}</p>
          </article>
        ))}
        {activities.length === 0 && (
          <p className="empty-state">Sem atividade ligada.</p>
        )}
      </section>
    </main>
  );
}
