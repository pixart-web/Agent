'use client';

import type { CodexRun } from '@agent/shared';
import { useParams } from '../../../../lib/route-params';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { StatusBadge } from '../../../../components/status-badge';
import { getCodexRun } from '../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';
import { apiMessage } from '../../../../lib/api-messages';

export default function CodexRunDetailPage() {
  const { user, loading } = useAuthenticatedUser();
  const params = useParams<{ run_id: string }>();
  const [run, setRun] = useState<CodexRun | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user || !params.run_id) return;
    void getCodexRun(params.run_id)
      .then(setRun)
      .catch(() => setError('Execução do Codex não encontrada.'));
  }, [params.run_id, user]);

  if (loading || !user)
    return (
      <main className="loading-page">A carregar a execução do Codex…</main>
    );

  return (
    <main>
      <DashboardNav user={user} />
      {error && <p className="workflow-alert">{error}</p>}
      {run && (
        <>
          <section className="section-heading">
            <div>
              <p className="eyebrow">{run.repository}</p>
              <h1>Execução do Codex</h1>
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
                <dt>Branch de trabalho</dt>
                <dd>{run.working_branch || 'Revisão só de leitura'}</dd>
              </div>
              <div>
                <dt>Commit</dt>
                <dd>{run.commit_sha || 'Nenhum'}</dd>
              </div>
              <div>
                <dt>Duração</dt>
                <dd>
                  {run.duration_ms === null ? '—' : `${run.duration_ms} ms`}
                </dd>
              </div>
              <div>
                <dt>Testes aprovados</dt>
                <dd>
                  {run.tests_passed === null
                    ? '—'
                    : run.tests_passed
                      ? 'Sim'
                      : 'Não'}
                </dd>
              </div>
              <div>
                <dt>Correlação</dt>
                <dd>{run.correlation_id}</dd>
              </div>
            </dl>
            <h2>Resumo</h2>
            <p>{run.summary || 'Pendentes'}</p>
            {run.error_message && (
              <p className="workflow-alert">{apiMessage(run.error_message)}</p>
            )}
            <h2>Ficheiros alterados</h2>
            <ul>
              {run.files_changed.map((file) => (
                <li key={file}>{file}</li>
              ))}
            </ul>
            <h2>Validação</h2>
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
