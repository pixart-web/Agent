'use client';

import type { CodexRun } from '@agent/shared';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { StatusBadge } from '../../../../components/status-badge';
import { getCodexRun } from '../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';

export default function CodexRunDetailPage() {
  const { user, loading } = useAuthenticatedUser();
  const params = useParams<{ run_id: string }>();
  const [run, setRun] = useState<CodexRun | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user || !params.run_id) return;
    void getCodexRun(params.run_id)
      .then(setRun)
      .catch(() => setError('Codex run not found.'));
  }, [params.run_id, user]);

  if (loading || !user)
    return <main className="loading-page">Loading Codex run…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      {error && <p className="workflow-alert">{error}</p>}
      {run && (
        <>
          <section className="section-heading">
            <div>
              <p className="eyebrow">{run.repository}</p>
              <h1>Codex run</h1>
            </div>
            <StatusBadge status={run.status} />
          </section>
          <section className="workflow-panel">
            <dl className="execution-meta">
              <div>
                <dt>Base</dt>
                <dd>{run.base_branch}</dd>
              </div>
              <div>
                <dt>Working branch</dt>
                <dd>{run.working_branch || 'Read-only review'}</dd>
              </div>
              <div>
                <dt>Commit</dt>
                <dd>{run.commit_sha || 'None'}</dd>
              </div>
              <div>
                <dt>Duration</dt>
                <dd>
                  {run.duration_ms === null ? '—' : `${run.duration_ms} ms`}
                </dd>
              </div>
              <div>
                <dt>Tests passed</dt>
                <dd>
                  {run.tests_passed === null
                    ? '—'
                    : run.tests_passed
                      ? 'Yes'
                      : 'No'}
                </dd>
              </div>
              <div>
                <dt>Correlation</dt>
                <dd>{run.correlation_id}</dd>
              </div>
            </dl>
            <h2>Summary</h2>
            <p>{run.summary || 'Pending'}</p>
            {run.error_message && (
              <p className="workflow-alert">{run.error_message}</p>
            )}
            <h2>Files changed</h2>
            <ul>
              {run.files_changed.map((file) => (
                <li key={file}>{file}</li>
              ))}
            </ul>
            <h2>Validation</h2>
            <ul>
              {run.tests_run.map((test) => (
                <li key={test}>{test}</li>
              ))}
            </ul>
          </section>
        </>
      )}
    </main>
  );
}
