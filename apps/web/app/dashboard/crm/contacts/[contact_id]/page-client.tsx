'use client';

import type { CrmActivity, CrmContact } from '@agent/shared';
import { useParams } from '../../../../../lib/route-params';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../../components/dashboard-nav';
import {
  getCrmContact,
  listCrmActivities,
  updateCrmContact,
} from '../../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../../lib/use-authenticated-user';
import { failureMessage } from '../../../../../lib/api-messages';

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
      .catch(() => setError('Não foi possível carregar este contacto.'));
  }, [contactId, user]);

  if (loading || !user)
    return <main className="loading-page">A carregar o contacto…</main>;
  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Contacto do CRM</p>
          <h1>{contact?.full_name || 'Contacto'}</h1>
          <p>{contact?.job_title || 'Sem cargo'}</p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {contact && (
        <section className="workflow-panel">
          <h2>Formas de contacto</h2>
          <label>
            Ciclo de vida
            <select
              value={contact.status}
              onChange={async (event) => {
                try {
                  setContact(
                    await updateCrmContact(contact.id, {
                      status: event.target.value,
                    }),
                  );
                } catch (failure) {
                  setError(
                    failureMessage(
                      failure,
                      'Não foi possível atualizar este contacto.',
                    ),
                  );
                }
              }}
            >
              <option value="active">Ativo</option>
              <option value="inactive">Inativo</option>
              <option value="archived">Arquivado</option>
            </select>
          </label>
          {contact.methods.map((method) => (
            <p key={method.id}>
              {method.method_type}: {method.value}{' '}
              {method.is_primary ? '· principal' : ''}
            </p>
          ))}
          <p>Website: {contact.website || 'Nenhum'}</p>
          <p>Tags: {contact.tags.join(', ') || 'Nenhum'}</p>
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
