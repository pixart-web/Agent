'use client';

import type {
  RiskLevel,
  TaskExecution,
  TaskExecutionStatus,
} from '@agent/shared';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import { StatusBadge } from '../../../components/status-badge';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import { listExecutions, WorkflowApiError } from '../../../lib/workflow-client';

export default function ExecutionsPage() {
  const { user, loading: authLoading } = useAuthenticatedUser();
  const [executions, setExecutions] = useState<TaskExecution[]>([]);
  const [status, setStatus] = useState<TaskExecutionStatus | ''>('');
  const [risk, setRisk] = useState<RiskLevel | ''>('');
  const [agent, setAgent] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    listExecutions({
      status: status || undefined,
      risk: risk || undefined,
      agent: agent || undefined,
    })
      .then(setExecutions)
      .catch((loadError) =>
        setError(
          loadError instanceof WorkflowApiError
            ? loadError.message
            : 'Unable to load executions.',
        ),
      );
  }, [user, status, risk, agent]);

  if (authLoading || !user) {
    return <main className="loading-page">Loading executions…</main>;
  }

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Kiko operations</p>
          <h1>Execution Center</h1>
          <p>
            PostgreSQL-backed attempts transported through Redis and Celery.
          </p>
        </div>
      </section>
      <section className="execution-filters">
        <select
          value={status}
          onChange={(e) =>
            setStatus(e.target.value as TaskExecutionStatus | '')
          }
        >
          <option value="">All statuses</option>
          {[
            'queued',
            'running',
            'succeeded',
            'failed',
            'retry_scheduled',
            'cancelled',
          ].map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <select
          value={risk}
          onChange={(e) => setRisk(e.target.value as RiskLevel | '')}
        >
          <option value="">All risks</option>
          <option>green</option>
          <option>yellow</option>
          <option>red</option>
        </select>
        <select value={agent} onChange={(e) => setAgent(e.target.value)}>
          <option value="">All agents</option>
          {['supervisor', 'marketing', 'sales', 'support', 'development'].map(
            (item) => (
              <option key={item}>{item}</option>
            ),
          )}
        </select>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <div className="execution-list">
        {executions.map((execution) => (
          <article className="workflow-panel execution-card" key={execution.id}>
            <div className="workflow-panel__heading">
              <div>
                <p className="eyebrow">Attempt #{execution.attempt_number}</p>
                <h2>{execution.tool_name}</h2>
              </div>
              <StatusBadge status={execution.status} />
            </div>
            <dl className="execution-meta">
              <div>
                <dt>Task</dt>
                <dd>{execution.task_id}</dd>
              </div>
              <div>
                <dt>Duration</dt>
                <dd>{execution.duration_ms ?? '—'} ms</dd>
              </div>
              <div>
                <dt>Worker</dt>
                <dd>{execution.worker_id ?? 'Not claimed'}</dd>
              </div>
              <div>
                <dt>Error</dt>
                <dd>{execution.error_message ?? '—'}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
      {!executions.length && (
        <p className="empty-state">No executions found.</p>
      )}
    </main>
  );
}
