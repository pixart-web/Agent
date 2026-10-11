'use client';

import type { AgentOverview } from '@agent/shared';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { StatusBadge } from '../../../../components/status-badge';
import {
  getAgentOverview,
  updateAgentConfiguration,
} from '../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading } = useAuthenticatedUser();
  const [overview, setOverview] = useState<AgentOverview | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
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
          <p
            className={`agent-operational agent-operational--${overview.operational_status}`}
          >
            {overview.operational_message}
          </p>
        </div>
      </section>
      <section className="workflow-panel">
        <h2>Workspace configuration</h2>
        <div className="agent-config-grid">
          <label>
            <span>Active</span>
            <input
              type="checkbox"
              checked={overview.configuration.enabled}
              disabled={saving}
              onChange={async (event) => {
                setSaving(true);
                setMessage('');
                try {
                  await updateAgentConfiguration(id, {
                    enabled: event.target.checked,
                  });
                  setOverview(await getAgentOverview(id));
                  setMessage('Configuration saved.');
                } catch {
                  setMessage(
                    'Only workspace administrators can change this configuration.',
                  );
                } finally {
                  setSaving(false);
                }
              }}
            />
          </label>
          <label>
            Approval policy
            <select
              value={overview.configuration.approval_policy}
              disabled={saving}
              onChange={async (event) => {
                setSaving(true);
                setMessage('');
                try {
                  await updateAgentConfiguration(id, {
                    approval_policy: event.target
                      .value as AgentOverview['configuration']['approval_policy'],
                  });
                  setOverview(await getAgentOverview(id));
                  setMessage('Configuration saved.');
                } catch {
                  setMessage('The configuration could not be saved.');
                } finally {
                  setSaving(false);
                }
              }}
            >
              <option value="platform_default">Platform default</option>
              <option value="risk_based">Risk based</option>
              <option value="always">Always require approval</option>
            </select>
          </label>
        </div>
        {message && (
          <p className="form-message" role="status">
            {message}
          </p>
        )}
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
