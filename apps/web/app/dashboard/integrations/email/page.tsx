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
import { confirmAction } from '../../../../lib/confirm';
import { startExternalAuthorization } from '../../../../lib/downloads';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';
import { CanEdit } from '../../../../lib/workspace-access';
import { label } from '../../../../lib/labels';

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
      .catch(() =>
        setError('Não foi possível carregar a integração de email.'),
      );
  }

  useEffect(() => {
    if (user) void refresh();
  }, [user]);

  async function handleConnect() {
    try {
      const value = await connectEmail();
      await startExternalAuthorization(value.authorization_url);
    } catch {
      setError('Não foi possível iniciar a autorização Google.');
    }
  }

  async function handleDisconnect(accountId: string) {
    if (!(await confirmAction('Desligar esta conta de email?'))) return;
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
          <p className="eyebrow">Integração</p>
          <h1>Email</h1>
          <p>
            As credenciais OAuth da Google ficam cifradas no servidor e nunca
            chegam ao browser.
          </p>
        </div>
        <CanEdit>
          <button
            className="primary-button"
            type="button"
            disabled={!integration?.enabled}
            onClick={() => void handleConnect()}
          >
            Ligar conta Google
          </button>
        </CanEdit>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {integration && (
        <section className="workflow-panel integration-health">
          <div>
            <p className="eyebrow">Estado operacional</p>
            <h2>{label(integration.operational_state)}</h2>
          </div>
          <p>
            {integration.unresolved_writes} entregas por confirmar ·{' '}
            {integration.pending_writes} pendentes · {integration.failed_writes}{' '}
            falhadas
          </p>
          <p>
            Last provider sync:{' '}
            {integration.last_sync_at
              ? new Date(integration.last_sync_at).toLocaleString('pt-PT')
              : 'Nunca'}
          </p>
          {integration.unresolved_writes > 0 && (
            <p className="workflow-alert">
              Do not retry automatically. Confirm delivery in Gmail before a
              human initiates a new action.
            </p>
          )}
        </section>
      )}
      <section className="workflow-panel">
        <h2>Contas ligadas</h2>
        <p>
          Envio:{' '}
          {integration?.send_enabled ? 'ativo com aprovação' : 'desativado'} ·
          Marcar como lido:{' '}
          {integration?.mark_read_enabled
            ? 'ativo com aprovação'
            : 'desativado'}
        </p>
        {accounts.length === 0 ? (
          <p className="empty-state">Nenhuma conta de email ligada.</p>
        ) : (
          <div className="agent-grid">
            {accounts.map((account) => (
              <article className="agent-card" key={account.id}>
                <p className="eyebrow">{account.provider}</p>
                <h3>{account.email_address}</h3>
                <p>Estado: {label(account.status)}</p>
                <p>Scopes: {account.scopes.join(', ')}</p>
                <CanEdit>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => void handleDisconnect(account.id)}
                  >
                    Desligar
                  </button>
                </CanEdit>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
