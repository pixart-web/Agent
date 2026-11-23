'use client';

import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import { KikoWorkspaceMode } from '../../../components/kiko/kiko-workspace';
import {
  getOperationsAnalytics,
  type OperationsAnalytics,
} from '../../../lib/operations-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function AnalyticsPage() {
  const { user, loading } = useAuthenticatedUser();
  const [report, setReport] = useState<OperationsAnalytics | null>(null);
  const [days, setDays] = useState(30);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    setError('');
    void getOperationsAnalytics(days)
      .then(setReport)
      .catch(() =>
        setError('Não foi possível carregar os relatórios operacionais.'),
      );
  }, [days, user]);

  if (loading || !user)
    return <main className="loading-page">A carregar os relatórios…</main>;

  const totals = report?.totals;
  const metrics = [
    ['Comandos', totals?.commands ?? 0],
    ['Execuções de agentes', totals?.agent_runs ?? 0],
    ['Execuções de ferramentas', totals?.tool_executions ?? 0],
    ['Ferramentas bem-sucedidas', totals?.successful_tool_executions ?? 0],
    ['Ferramentas falhadas', totals?.failed_tool_executions ?? 0],
    ['Tokens', totals?.total_tokens ?? 0],
    ['Execuções de automatizações', totals?.automation_runs ?? 0],
    ['Automatizações falhadas', totals?.failed_automation_runs ?? 0],
  ] as const;

  return (
    <main>
      <DashboardNav user={user} />
      <KikoWorkspaceMode
        mode="analysis"
        state={error ? 'error' : report ? 'idle' : 'thinking'}
        detail={
          error ||
          (report
            ? `Atividade dos últimos ${days} dias, calculada a partir dos registos guardados.`
            : 'A recolher os registos…')
        }
      />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Operações medidas</p>
          <h1>Relatórios</h1>
          <p>
            Atividade do workspace calculada a partir dos registos de execução
            guardados.
          </p>
        </div>
        <label>
          Período
          <select
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
          >
            <option value={7}>7 dias</option>
            <option value={30}>30 dias</option>
            <option value={90}>90 dias</option>
          </select>
        </label>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <section className="agent-grid" aria-label="Totais operacionais">
        {metrics.map(([label, value]) => (
          <article className="agent-card" key={label}>
            <p className="eyebrow">{label}</p>
            <h2>{value.toLocaleString('pt-PT')}</h2>
          </article>
        ))}
      </section>
      <section className="workflow-panel">
        <div className="workflow-panel__heading">
          <div>
            <p className="eyebrow">Visibilidade de custos</p>
            <h2>Custo estimado de IA</h2>
          </div>
        </div>
        <p>
          {report?.estimated_cost_minor === null
            ? 'Indisponível — não há uma fonte de preços verificada configurada.'
            : `${report?.estimated_cost_minor} ${report?.estimated_cost_currency}`}
        </p>
      </section>
      <section className="workflow-panel">
        <div className="workflow-panel__heading">
          <div>
            <p className="eyebrow">Atividade diária</p>
            <h2>Tendência</h2>
          </div>
        </div>
        <div className="activity-list">
          {report?.trends
            .filter((point) =>
              [
                point.commands,
                point.agent_runs,
                point.tool_executions,
                point.automation_runs,
              ].some(Boolean),
            )
            .map((point) => (
              <article className="activity-item" key={point.date}>
                <strong>
                  {new Date(`${point.date}T00:00:00`).toLocaleDateString(
                    'pt-PT',
                  )}
                </strong>
                <p>
                  {point.commands} comandos · {point.agent_runs} execuções de
                  agentes · {point.tool_executions} ferramentas ·{' '}
                  {point.automation_runs} automatizações
                </p>
              </article>
            ))}
          {report && !report.trends.some((point) => point.commands > 0) && (
            <p className="empty-state">Sem atividade neste período.</p>
          )}
        </div>
      </section>
    </main>
  );
}
