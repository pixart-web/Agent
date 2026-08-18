'use client';

import type { AgentOverview } from '@agent/shared';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { StatusBadge } from '../../../../components/status-badge';
import { getAgentOverview } from '../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading } = useAuthenticatedUser();
  const [overview, setOverview] = useState<AgentOverview | null>(null);
  useEffect(() => {
    if (user) void getAgentOverview(id).then(setOverview);
  }, [id, user]);
  if (loading || !user || !overview)
    return <main className="loading-page">Loading agent…</main>;
  return (
    <main>
      <DashboardNav user={user} />
      <section className="hero">
        <div>
          <p className="eyebrow">{overview.capabilities.prompt_version}</p>
          <h1>{overview.capabilities.name} Agent</h1>
          <p>{overview.capabilities.description}</p>
        </div>
      </section>
      <section className="workflow-panel">
        <h2>Capabilities</h2>
        <p>Maximum {overview.capabilities.max_actions} actions per task</p>
        <div className="tool-chips">
          {overview.capabilities.allowed_tools.map((tool) => (
            <code key={tool}>{tool}</code>
          ))}
        </div>
      </section>
      <section className="workflow-panel">
        <h2>Recent runs · {overview.success_rate}% success</h2>
        {overview.recent_runs.map((run) => (
          <div className="action-row" key={run.id}>
            <div>
              <strong>
                {run.proposal_summary ?? run.error_message ?? 'Agent run'}
              </strong>
              <span>
                {' '}
                · {run.model} · {run.total_tokens ?? 0} tokens
              </span>
            </div>
            <StatusBadge status={run.status} />
          </div>
        ))}
      </section>
    </main>
  );
}
