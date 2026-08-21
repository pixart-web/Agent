'use client';

import type { CodexIntegrationStatus, CodexRun } from '@agent/shared';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import { StatusBadge } from '../../../components/status-badge';
import {
  getCodexIntegrationStatus,
  listCodexRuns,
} from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function CodexRunsPage() {
  const { user, loading } = useAuthenticatedUser();
  const [runs, setRuns] = useState<CodexRun[]>([]);
  const [integration, setIntegration] = useState<CodexIntegrationStatus | null>(
    null,
  );
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    void Promise.all([listCodexRuns(), getCodexIntegrationStatus()])
      .then(([items, status]) => {
        setRuns(items);
        setIntegration(status);
      })
      .catch(() => setError('Unable to load Codex runs.'));
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">Loading Codex…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Development execution</p>
          <h1>Codex runs</h1>
          <p>
            Safe run metadata only. Terminal logs and credentials are never
            shown.
          </p>
        </div>
        <span>
          {integration?.enabled && integration?.credential_configured
            ? 'Ready'
            : 'Not configured'}
        </span>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <div className="approval-grid">
        {runs.map((run) => (
          <Link
            className="workflow-panel agent-card--link"
            href={`/dashboard/codex/${run.id}`}
            key={run.id}
          >
            <div className="workflow-panel__heading">
              <div>
                <p className="eyebrow">{run.repository}</p>
                <h2>
                  {run.working_branch || `PR #${run.pull_request_number}`}
                </h2>
              </div>
              <StatusBadge status={run.status} />
            </div>
            <p>{run.summary || run.instruction}</p>
            <small>{new Date(run.created_at).toLocaleString()}</small>
          </Link>
        ))}
      </div>
      {!runs.length && !error && (
        <p className="empty-state">No Codex runs yet.</p>
      )}
    </main>
  );
}
