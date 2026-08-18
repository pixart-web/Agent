'use client';

import { AGENT_CATALOG, type AgentId, type AgentOverview } from '@agent/shared';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../components/dashboard-nav';
import { getAgentOverview } from '../../lib/workflow-client';
import { useAuthenticatedUser } from '../../lib/use-authenticated-user';

type ApiState = 'checking' | 'online' | 'offline';

function AgentMetrics({ agentId }: { agentId: AgentId }) {
  const [overview, setOverview] = useState<AgentOverview | null>(null);

  useEffect(() => {
    if (agentId === 'supervisor') return;
    void getAgentOverview(agentId)
      .then(setOverview)
      .catch(() => undefined);
  }, [agentId]);

  return (
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
  );
}
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export default function DashboardPage() {
  const { user, loading } = useAuthenticatedUser();
  const [apiState, setApiState] = useState<ApiState>('checking');

  useEffect(() => {
    let active = true;

    async function checkApi() {
      try {
        const response = await fetch(`${apiUrl}/health`);
        if (active) setApiState(response.ok ? 'online' : 'offline');
      } catch {
        if (active) setApiState('offline');
      }
    }

    void checkApi();
    return () => {
      active = false;
    };
  }, []);

  if (loading || !user) {
    return (
      <main className="loading-page">
        <p aria-live="polite">Restoring your secure session…</p>
      </main>
    );
  }

  return (
    <main>
      <DashboardNav user={user} />

      <section className="hero">
        <div>
          <p className="eyebrow">Pixart operations</p>
          <h1>Kiko</h1>
          <p className="subtitle">Pixart AI Operating System</p>
        </div>

        <div
          className={`api-status api-status--${apiState}`}
          aria-live="polite"
        >
          <span className="status-dot" aria-hidden="true" />
          <div>
            <span className="status-label">API status</span>
            <strong>{apiState}</strong>
          </div>
        </div>
      </section>

      <section className="agents" aria-labelledby="agents-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Core team</p>
            <h2 id="agents-title">Agent network</h2>
          </div>
          <span>{AGENT_CATALOG.length} agents configured</span>
        </div>

        <div className="agent-grid">
          {AGENT_CATALOG.map((agent, index) => (
            <article className="agent-card" key={agent.id}>
              <div className="agent-card__topline">
                <span className="agent-index">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="ready-pill">Ready</span>
              </div>
              <h3>{agent.name}</h3>
              <p>{agent.description}</p>
              <AgentMetrics agentId={agent.id} />
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
