'use client';

import type {
  RiskLevel,
  TaskExecution,
  TaskExecutionStatus,
} from '@agent/shared';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import { StatusBadge } from '../../../components/status-badge';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import { listExecutions, WorkflowApiError } from '../../../lib/workflow-client';
import { label } from '../../../lib/labels';
import { apiMessage } from '../../../lib/api-messages';

export default function ExecutionsPage() {
  const { user, loading: authLoading } = useAuthenticatedUser();
  const [executions, setExecutions] = useState<TaskExecution[]>([]);
  const [status, setStatus] = useState<TaskExecutionStatus | ''>('');
  const [risk, setRisk] = useState<RiskLevel | ''>('');
  const [agent, setAgent] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    listExecutions({
      status: status || undefined,
      risk: risk || undefined,
      agent: agent || undefined,
    })
      .then(setExecutions)
      .catch((loadError) =>
        setError(
          loadError instanceof WorkflowApiError
            ? loadError.message
            : 'Não foi possível carregar as execuções.',
        ),
      );
  }, [user, status, risk, agent]);

  if (authLoading || !user) {
    return <main className="loading-page">A carregar as execuções…</main>;
  }

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Operações do Kiko</p>
          <h1>Centro de execução</h1>
          <p>
            Tentativas guardadas em PostgreSQL e transportadas por Redis e
            Celery.
          </p>
        </div>
      </section>
      <section className="execution-filters">
        <select
          aria-label="Filtrar por estado"
          value={status}
          onChange={(e) =>
            setStatus(e.target.value as TaskExecutionStatus | '')
          }
        >
          <option value="">Todos os estados</option>
          {[
            'queued',
            'running',
            'succeeded',
            'failed',
            'retry_scheduled',
            'cancelled',
          ].map((item) => (
            <option key={item} value={item}>
              {label(item)}
            </option>
          ))}
        </select>
        <select
          aria-label="Filtrar por risco"
          value={risk}
          onChange={(e) => setRisk(e.target.value as RiskLevel | '')}
        >
          <option value="">Todos os riscos</option>
          <option value="green">Verde</option>
          <option value="yellow">Amarelo</option>
          <option value="red">Vermelho</option>
        </select>
        <select
          aria-label="Filtrar por agente"
          value={agent}
          onChange={(e) => setAgent(e.target.value)}
        >
          <option value="">Todos os agentes</option>
          {['supervisor', 'marketing', 'sales', 'support', 'development'].map(
            (item) => (
              <option key={item} value={item}>
                {label(item)}
              </option>
            ),
          )}
        </select>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <div className="execution-list">
        {executions.map((execution) => (
          <article className="workflow-panel execution-card" key={execution.id}>
            <div className="workflow-panel__heading">
              <div>
                <p className="eyebrow">Attempt #{execution.attempt_number}</p>
                <h2>{execution.tool_name}</h2>
              </div>
              <StatusBadge status={execution.status} />
            </div>
            <dl className="execution-meta">
              <div>
                <dt>Tarefa</dt>
                <dd>{execution.task_id}</dd>
              </div>
              <div>
                <dt>Duração</dt>
                <dd>{execution.duration_ms ?? '—'} ms</dd>
              </div>
              <div>
                <dt>Worker</dt>
                <dd>{execution.worker_id ?? 'Não reclamado'}</dd>
              </div>
              <div>
                <dt>Erro</dt>
                <dd>
                  {execution.error_message
                    ? apiMessage(execution.error_message)
                    : '—'}
                </dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
      {!executions.length && (
        <p className="empty-state">Nenhuma execução encontrada.</p>
      )}
    </main>
  );
}
