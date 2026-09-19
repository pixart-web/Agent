'use client';

import type {
  CalendarIntegrationStatus,
  EmailIntegrationStatus,
  GitHubIntegrationStatus,
} from '@agent/shared';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  getCalendarIntegrationStatus,
  getEmailIntegrationStatus,
  getGitHubIntegrationStatus,
} from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function IntegrationsPage() {
  const { user, loading } = useAuthenticatedUser();
  const [github, setGitHub] = useState<GitHubIntegrationStatus | null>(null);
  const [email, setEmail] = useState<EmailIntegrationStatus | null>(null);
  const [calendar, setCalendar] = useState<CalendarIntegrationStatus | null>(
    null,
  );

  useEffect(() => {
    if (user) {
      void getGitHubIntegrationStatus().then(setGitHub);
      void getEmailIntegrationStatus().then(setEmail);
      void getCalendarIntegrationStatus().then(setCalendar);
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
        <Link
          className="agent-card agent-card--link"
          href="/dashboard/integrations/email"
        >
          <p className="eyebrow">Communication</p>
          <h2>Email</h2>
          <p>
            Status: {email?.connected_accounts ? 'Connected' : 'Not connected'}
          </p>
          <p>Provider: {email?.provider || 'gmail'}</p>
        </Link>
        <Link
          className="agent-card agent-card--link"
          href="/dashboard/integrations/calendar"
        >
          <p className="eyebrow">Scheduling</p>
          <h2>Calendar</h2>
          <p>
            Status:{' '}
            {calendar?.connected_accounts ? 'Connected' : 'Not connected'}
          </p>
          <p>Provider: {calendar?.provider || 'google_calendar'}</p>
        </Link>{' '}
      </div>
    </main>
  );
}
