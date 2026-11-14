'use client';

import type { CalendarAccount, CalendarIntegrationStatus } from '@agent/shared';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import {
  connectCalendar,
  disconnectCalendar,
  getCalendarIntegrationStatus,
  listCalendarAccounts,
} from '../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';

export default function CalendarIntegrationPage() {
  const { user, loading } = useAuthenticatedUser();
  const [integration, setIntegration] =
    useState<CalendarIntegrationStatus | null>(null);
  const [accounts, setAccounts] = useState<CalendarAccount[]>([]);
  const [error, setError] = useState('');

  function refresh() {
    return Promise.all([getCalendarIntegrationStatus(), listCalendarAccounts()])
      .then(([status, values]) => {
        setIntegration(status);
        setAccounts(values);
      })
      .catch(() => setError('Unable to load Calendar integration.'));
  }

  useEffect(() => {
    if (user) void refresh();
  }, [user]);

  async function handleConnect() {
    try {
      const value = await connectCalendar();
      window.location.assign(value.authorization_url);
    } catch {
      setError('Unable to start Google Calendar authorization.');
    }
  }

  async function handleDisconnect(accountId: string) {
    if (!window.confirm('Disconnect this Calendar account?')) return;
    await disconnectCalendar(accountId);
    await refresh();
  }

  if (loading || !user)
    return <main className="loading-page">Loading Calendar…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Integration</p>
          <h1>Google Calendar</h1>
          <p>
            OAuth credentials stay encrypted on the backend. Calendar content is
            untrusted.
          </p>
        </div>
        <button
          className="primary-button"
          type="button"
          disabled={!integration?.enabled}
          onClick={() => void handleConnect()}
        >
          Connect Google Calendar
        </button>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {integration && (
        <section className="workflow-panel integration-health">
          <div>
            <p className="eyebrow">Operational state</p>
            <h2>{integration.operational_state.replaceAll('_', ' ')}</h2>
          </div>
          <p>
            {integration.unresolved_writes} delivery outcomes require
            reconciliation · {integration.pending_writes} pending ·{' '}
            {integration.failed_writes} failed
          </p>
          <p>
            Last provider sync:{' '}
            {integration.last_sync_at
              ? new Date(integration.last_sync_at).toLocaleString()
              : 'Never'}
          </p>
          {integration.unresolved_writes > 0 && (
            <p className="workflow-alert">
              Do not retry automatically. Confirm the event in Google Calendar
              before a human initiates a new action.
            </p>
          )}
        </section>
      )}
      <section className="workflow-panel">
        <h2>Connected accounts</h2>
        <p>
          Writes:{' '}
          {integration?.write_enabled ? 'enabled with approval' : 'disabled'}
        </p>
        {accounts.length === 0 ? (
          <p className="empty-state">No Calendar account connected.</p>
        ) : (
          <div className="agent-grid">
            {accounts.map((account) => (
              <article className="agent-card" key={account.id}>
                <p className="eyebrow">{account.provider}</p>
                <h3>{account.email_address}</h3>
                <p>Status: {account.status}</p>
                <p>Scopes: {account.scopes.join(', ')}</p>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => void handleDisconnect(account.id)}
                >
                  Disconnect
                </button>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
