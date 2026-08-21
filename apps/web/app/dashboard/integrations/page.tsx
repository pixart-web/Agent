'use client';

import type { GitHubIntegrationStatus } from '@agent/shared';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import { getGitHubIntegrationStatus } from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function IntegrationsPage() {
  const { user, loading } = useAuthenticatedUser();
  const [github, setGitHub] = useState<GitHubIntegrationStatus | null>(null);

  useEffect(() => {
    if (user) {
      void getGitHubIntegrationStatus().then(setGitHub);
    }
  }, [user]);

  if (loading || !user) {
    return <main className="loading-page">Loading integrations…</main>;
  }

  const connected = Boolean(github?.enabled && github?.credential_configured);

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">External services</p>
          <h1>Integrations</h1>
          <p>Credentials remain server-side and are never shown here.</p>
        </div>
      </section>
      <div className="agent-grid">
        <Link
          className="agent-card agent-card--link"
          href="/dashboard/integrations/github"
        >
          <p className="eyebrow">Development tools</p>
          <h2>GitHub</h2>
          <p>Status: {connected ? 'Connected' : 'Not configured'}</p>
          <p>
            Allowed repositories:{' '}
            {github?.allowed_repositories.join(', ') || 'None'}
          </p>
        </Link>
      </div>
    </main>
  );
}
