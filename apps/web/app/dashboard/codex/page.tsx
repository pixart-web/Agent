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
      .catch(() =>
        setError('Não foi possível carregar as execuções do Codex.'),
      );
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">A carregar o Codex…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Execução de desenvolvimento</p>
          <h1>Execuções do Codex</h1>
          <p>
            Só metadados seguros da execução. Registos do terminal e credenciais
            nunca são mostrados.
          </p>
        </div>
        <span>
          {integration?.enabled && integration?.credential_configured
            ? 'Pronta'
            : 'Não configurado'}
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
            <small>{new Date(run.created_at).toLocaleString('pt-PT')}</small>
          </Link>
        ))}
      </div>
      {!runs.length && !error && (
        <p className="empty-state">Ainda não há execuções do Codex.</p>
      )}
    </main>
  );
}
