'use client';

import { AGENT_CATALOG, type AgentOverview } from '@agent/shared';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import { getAgentOverview } from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

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
    return <main className="loading-page">Loading agents…</main>;
  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Kiko team</p>
          <h1>Specialized Agents</h1>
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
              <dl className="agent-metrics">
                <div>
                  <dt>Pending</dt>
                  <dd>{overview?.tasks_pending ?? 0}</dd>
                </div>
                <div>
                  <dt>Running</dt>
                  <dd>{overview?.tasks_running ?? 0}</dd>
                </div>
                <div>
                  <dt>Approval</dt>
                  <dd>{overview?.tasks_waiting_approval ?? 0}</dd>
                </div>
                <div>
                  <dt>Failed</dt>
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
