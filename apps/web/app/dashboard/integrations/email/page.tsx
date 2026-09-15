'use client';

import type { EmailAccount, EmailIntegrationStatus } from '@agent/shared';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import {
  connectEmail,
  disconnectEmail,
  getEmailIntegrationStatus,
  listEmailAccounts,
} from '../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';

export default function EmailIntegrationPage() {
  const { user, loading } = useAuthenticatedUser();
  const [integration, setIntegration] = useState<EmailIntegrationStatus | null>(
    null,
  );
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [error, setError] = useState('');

  function refresh() {
    return Promise.all([getEmailIntegrationStatus(), listEmailAccounts()])
      .then(([status, values]) => {
        setIntegration(status);
        setAccounts(values);
      })
      .catch(() => setError('Unable to load email integration.'));
  }

  useEffect(() => {
    if (user) void refresh();
  }, [user]);

  async function handleConnect() {
    try {
      const value = await connectEmail();
      window.location.assign(value.authorization_url);
    } catch {
      setError('Unable to start Google authorization.');
    }
  }

  async function handleDisconnect(accountId: string) {
    if (!window.confirm('Disconnect this email account?')) return;
    await disconnectEmail(accountId);
    await refresh();
  }

  if (loading || !user)
    return <main className="loading-page">Loading email&</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Integration</p>
          <h1>Email</h1>
          <p>
            Google OAuth credentials remain encrypted on the backend and never
            reach the browser.
          </p>
        </div>
        <button
          className="primary-button"
          type="button"
          disabled={!integration?.enabled}
          onClick={() => void handleConnect()}
        >
          Connect Google account
        </button>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <section className="workflow-panel">
        <h2>Connected accounts</h2>
        <p>
          Sending:{' '}
          {integration?.send_enabled ? 'enabled with approval' : 'disabled'} �
          Mark read:{' '}
          {integration?.mark_read_enabled
            ? 'enabled with approval'
            : 'disabled'}
        </p>
        {accounts.length === 0 ? (
          <p className="empty-state">No email account connected.</p>
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
