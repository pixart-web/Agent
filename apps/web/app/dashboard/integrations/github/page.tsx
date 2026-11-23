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
      .catch(() =>
        setError('Não foi possível carregar o estado da integração GitHub.'),
      );
  }, [user]);

  if (loading || !user) {
    return <main className="loading-page">A carregar o GitHub…</main>;
  }

  const connected = Boolean(status?.enabled && status?.credential_configured);

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Integração</p>
          <h1>GitHub</h1>
          <p>
            O acesso aos repositórios é limitado a uma lista. As escritas só
            correm pelo motor de execução e exigem aprovação.
          </p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <section className="workflow-panel">
        <div className="workflow-panel__heading">
          <div>
            <span className="eyebrow">Estado</span>
            <h2>{connected ? 'Ligado' : 'Não configurado'}</h2>
          </div>
        </div>
        <dl className="execution-meta">
          <div>
            <dt>Ativo</dt>
            <dd>{status?.enabled ? 'Sim' : 'Não'}</dd>
          </div>
          <div>
            <dt>Credencial configurada</dt>
            <dd>{status?.credential_configured ? 'Sim' : 'Não'}</dd>
          </div>
          <div>
            <dt>Repositórios permitidos</dt>
            <dd>{status?.allowed_repositories.join(', ') || 'Nenhum'}</dd>
          </div>
        </dl>
        <p>
          O token só é obtido dentro do worker no momento da execução e nunca
          chega ao browser.
        </p>
      </section>
    </main>
  );
}
