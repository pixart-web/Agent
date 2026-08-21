'use client';

import type { GitHubIntegrationStatus } from '@agent/shared';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { getGitHubIntegrationStatus } from '../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';

export default function GitHubIntegrationPage() {
  const { user, loading } = useAuthenticatedUser();
  const [status, setStatus] = useState<GitHubIntegrationStatus | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    void getGitHubIntegrationStatus()
      .then(setStatus)
      .catch(() => setError('Unable to load GitHub integration status.'));
  }, [user]);

  if (loading || !user) {
    return <main className="loading-page">Loading GitHub…</main>;
  }

  const connected = Boolean(status?.enabled && status?.credential_configured);

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Integration</p>
          <h1>GitHub</h1>
          <p>
            Repository access is allowlisted. Writes run only through the
            Execution Engine and require approval.
          </p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <section className="workflow-panel">
        <div className="workflow-panel__heading">
          <div>
            <span className="eyebrow">Status</span>
            <h2>{connected ? 'Connected' : 'Not configured'}</h2>
          </div>
        </div>
        <dl className="execution-meta">
          <div>
            <dt>Enabled</dt>
            <dd>{status?.enabled ? 'Yes' : 'No'}</dd>
          </div>
          <div>
            <dt>Credential configured</dt>
            <dd>{status?.credential_configured ? 'Yes' : 'No'}</dd>
          </div>
          <div>
            <dt>Allowed repositories</dt>
            <dd>{status?.allowed_repositories.join(', ') || 'None'}</dd>
          </div>
        </dl>
        <p>
          The token is resolved only inside the worker at execution time and is
          never returned to the browser.
        </p>
      </section>
    </main>
  );
}
