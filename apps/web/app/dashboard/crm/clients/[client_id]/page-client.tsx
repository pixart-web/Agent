'use client';

import type { CrmClient360 } from '@agent/shared';
import Link from 'next/link';
import { useParams } from '../../../../../lib/route-params';
import { useEffect, useState } from 'react';

import { ClientInsight } from '../../../../../components/client-insight';
import { DashboardNav } from '../../../../../components/dashboard-nav';
import {
  getCrmClient360,
  updateCrmClient,
} from '../../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../../lib/use-authenticated-user';
import { label } from '../../../../../lib/labels';
import { failureMessage } from '../../../../../lib/api-messages';

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
      .catch(() => setError('Não foi possível carregar este cliente.'));
  }, [clientId, user]);

  if (loading || !user)
    return <main className="loading-page">A carregar o cliente…</main>;

  const client = view?.client;
  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Cliente 360 · contexto governado</p>
          <h1>{client?.organization.name || 'Cliente'}</h1>
          <p>
            {client
              ? client.lifecycle_status +
                ' · ' +
                (client.industry || 'Sem setor')
              : 'A carregar o contexto de negócio…'}
          </p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {view && (
        <>
          <section className="workflow-panel">
            <h2>Visão geral</h2>
            <label>
              Ciclo de vida
              <select
                value={view.client.lifecycle_status}
                onChange={async (event) => {
                  try {
                    const updated = await updateCrmClient(view.client.id, {
                      lifecycle_status: event.target.value,
                    });
                    setView({ ...view, client: updated });
                  } catch (failure) {
                    setError(
                      failureMessage(
                        failure,
                        'Não foi possível atualizar este cliente.',
                      ),
                    );
                  }
                }}
              >
                <option value="prospect">Potencial cliente</option>
                <option value="active">Ativo</option>
                <option value="paused">Em pausa</option>
                <option value="former">Antigo</option>
                <option value="archived">Arquivado</option>
              </select>
            </label>
            <p>{view.client.summary || 'Sem resumo do cliente.'}</p>
            <p>
              Owner: {view.client.owner_user_id} · CRM facts are separated from
              model-generated summaries.
            </p>
          </section>

          <section className="workflow-panel">
            <h2>Contactos</h2>
            <div className="agent-grid">
              {view.contacts.map((contact) => (
                <Link
                  className="agent-card agent-card--link"
                  href={'/dashboard/crm/contacts/' + contact.id}
                  key={contact.id}
                >
                  <p className="eyebrow">{label(contact.status)}</p>
                  <h3>{contact.full_name}</h3>
                  <p>{contact.job_title || 'Sem cargo'}</p>
                </Link>
              ))}
            </div>
            {view.contacts.length === 0 && (
              <p className="empty-state">Sem contactos.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Emails e reuniões</h2>
            {[...view.emails, ...view.meetings].map((activity) => (
              <article className="agent-card" key={activity.id}>
                <p className="eyebrow">{activity.activity_type}</p>
                <h3>{activity.subject}</h3>
                <p>{new Date(activity.occurred_at).toLocaleString('pt-PT')}</p>
              </article>
            ))}
            {view.emails.length + view.meetings.length === 0 && (
              <p className="empty-state">Sem emails ou reuniões ligados.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Projetos</h2>
            <div className="agent-grid">
              {view.projects.map((project) => (
                <article className="agent-card" key={project.id}>
                  <p className="eyebrow">{label(project.status)}</p>
                  <h3>{project.name}</h3>
                  <p>{project.description || 'Sem descrição'}</p>
                  <p>Due: {project.due_on || 'Não agendado'}</p>
                </article>
              ))}
            </div>
            {view.projects.length === 0 && (
              <p className="empty-state">Sem projetos.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Tarefas</h2>
            {view.tasks.map((task) => (
              <article className="agent-card" key={task.id}>
                <p className="eyebrow">
                  {label(task.status)} · {task.agent_id}
                </p>
                <h3>{task.title}</h3>
              </article>
            ))}
            {view.tasks.length === 0 && (
              <p className="empty-state">Sem tarefas ligadas.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Oportunidades</h2>
            <div className="agent-grid">
              {view.opportunities.map((opportunity) => (
                <article className="agent-card" key={opportunity.id}>
                  <p className="eyebrow">
                    {label(opportunity.status)} · {opportunity.probability}%
                  </p>
                  <h3>{opportunity.title}</h3>
                  <p>{money(opportunity.amount_minor, opportunity.currency)}</p>
                </article>
              ))}
            </div>
            {view.opportunities.length === 0 && (
              <p className="empty-state">Sem oportunidades.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Notas e atividade</h2>
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
              <p className="empty-state">Sem notas nem atividade.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Perspetivas do Kiko</h2>
            {view.insights.map((insight, index) => (
              <ClientInsight insight={insight} key={index} />
            ))}
            {view.insights.length === 0 && (
              <p className="empty-state">Sem perspetivas disponíveis.</p>
            )}
          </section>

          <section className="workflow-panel">
            <h2>Histórico</h2>
            {view.history.map((item) => (
              <p key={item.id}>
                {item.entity_type} · {label(item.event_type)} ·{' '}
                {new Date(item.created_at).toLocaleString('pt-PT')}
              </p>
            ))}
          </section>
        </>
      )}
    </main>
  );
}
