'use client';

import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  getOperationsAnalytics,
  type OperationsAnalytics,
} from '../../../lib/operations-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function AnalyticsPage() {
  const { user, loading } = useAuthenticatedUser();
  const [report, setReport] = useState<OperationsAnalytics | null>(null);
  const [days, setDays] = useState(30);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    setError('');
    void getOperationsAnalytics(days)
      .then(setReport)
      .catch(() => setError('Unable to load operational analytics.'));
  }, [days, user]);

  if (loading || !user)
    return <main className="loading-page">Loading analytics…</main>;

  const totals = report?.totals;
  const metrics = [
    ['Commands', totals?.commands ?? 0],
    ['Agent runs', totals?.agent_runs ?? 0],
    ['Tool executions', totals?.tool_executions ?? 0],
    ['Successful tools', totals?.successful_tool_executions ?? 0],
    ['Failed tools', totals?.failed_tool_executions ?? 0],
    ['Tokens', totals?.total_tokens ?? 0],
    ['Automation runs', totals?.automation_runs ?? 0],
    ['Failed automations', totals?.failed_automation_runs ?? 0],
  ] as const;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Measured operations</p>
          <h1>Analytics</h1>
          <p>Workspace activity derived from persisted execution records.</p>
        </div>
        <label>
          Period
          <select
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
          >
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
        </label>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <section className="agent-grid" aria-label="Operational totals">
        {metrics.map(([label, value]) => (
          <article className="agent-card" key={label}>
            <p className="eyebrow">{label}</p>
            <h2>{value.toLocaleString()}</h2>
          </article>
        ))}
      </section>
      <section className="workflow-panel">
        <div className="workflow-panel__heading">
          <div>
            <p className="eyebrow">Cost visibility</p>
            <h2>Estimated AI cost</h2>
          </div>
        </div>
        <p>
          {report?.estimated_cost_minor === null
            ? 'Unavailable — no verified provider pricing source is configured.'
            : `${report?.estimated_cost_minor} ${report?.estimated_cost_currency}`}
        </p>
      </section>
      <section className="workflow-panel">
        <div className="workflow-panel__heading">
          <div>
            <p className="eyebrow">Daily activity</p>
            <h2>Trend</h2>
          </div>
        </div>
        <div className="activity-list">
          {report?.trends
            .filter((point) =>
              [
                point.commands,
                point.agent_runs,
                point.tool_executions,
                point.automation_runs,
              ].some(Boolean),
            )
            .map((point) => (
              <article className="activity-item" key={point.date}>
                <strong>
                  {new Date(`${point.date}T00:00:00`).toLocaleDateString()}
                </strong>
                <p>
                  {point.commands} commands · {point.agent_runs} agent runs ·{' '}
                  {point.tool_executions} tools · {point.automation_runs}{' '}
                  automations
                </p>
              </article>
            ))}
          {report && !report.trends.some((point) => point.commands > 0) && (
            <p className="empty-state">No activity in this period.</p>
          )}
        </div>
      </section>
    </main>
  );
}
