'use client';

import { AGENT_CATALOG, type AgentOverview } from '@agent/shared';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import { getAgentOverview } from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import { operationalMessage } from '../../../lib/labels';

const SPECIALISTS = AGENT_CATALOG.filter((agent) => agent.id !== 'supervisor');

export default function AgentsPage() {
  const { user, loading } = useAuthenticatedUser();
  const [overviews, setOverviews] = useState<Record<string, AgentOverview>>({});
  useEffect(() => {
    if (!user) return;
    void Promise.all(
      SPECIALISTS.map(
        async (agent) => [agent.id, await getAgentOverview(agent.id)] as const,
      ),
    ).then((pairs) => setOverviews(Object.fromEntries(pairs)));
  }, [user]);
  if (loading || !user)
    return <main className="loading-page">A carregar os agentes…</main>;
  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Equipa Kiko</p>
          <h1>Agentes especializados</h1>
        </div>
      </section>
      <div className="agent-grid">
        {SPECIALISTS.map((agent) => {
          const overview = overviews[agent.id];
          return (
            <Link
              className="agent-card agent-card--link"
              href={'/dashboard/agents/' + agent.id}
              key={agent.id}
            >
              <h2>{agent.name}</h2>
              <p>{agent.description}</p>
              <p
                className={`agent-operational agent-operational--${overview?.operational_status ?? 'unavailable'}`}
              >
                {overview
                  ? operationalMessage(overview.operational_message)
                  : 'A verificar o fornecedor…'}
              </p>
              <dl className="agent-metrics">
                <div>
                  <dt>Pendentes</dt>
                  <dd>{overview?.tasks_pending ?? 0}</dd>
                </div>
                <div>
                  <dt>A decorrer</dt>
                  <dd>{overview?.tasks_running ?? 0}</dd>
                </div>
                <div>
                  <dt>Aprovação</dt>
                  <dd>{overview?.tasks_waiting_approval ?? 0}</dd>
                </div>
                <div>
                  <dt>Falhou</dt>
                  <dd>{overview?.tasks_failed ?? 0}</dd>
                </div>
              </dl>
            </Link>
          );
        })}
      </div>
    </main>
  );
}
