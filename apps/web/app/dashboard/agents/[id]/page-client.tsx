'use client';

import { AGENT_CATALOG, type AgentOverview } from '@agent/shared';
import { useParams } from '../../../../lib/route-params';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { StatusBadge } from '../../../../components/status-badge';
import {
  getAgentOverview,
  updateAgentConfiguration,
} from '../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';
import { aiErrorHint } from '../../../../lib/ai-errors';
import { operationalMessage } from '../../../../lib/labels';

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading } = useAuthenticatedUser();
  const [overview, setOverview] = useState<AgentOverview | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  useEffect(() => {
    if (user) void getAgentOverview(id).then(setOverview);
  }, [id, user]);
  if (loading || !user || !overview)
    return <main className="loading-page">A carregar o agente…</main>;
  return (
    <main>
      <DashboardNav user={user} />
      <section className="hero">
        <div>
          <p className="eyebrow">{overview.capabilities.prompt_version}</p>
          <h1>
            Agente{' '}
            {AGENT_CATALOG.find((agent) => agent.id === id)?.name ??
              overview.capabilities.name}
          </h1>
          <p>
            {AGENT_CATALOG.find((agent) => agent.id === id)?.description ??
              overview.capabilities.description}
          </p>
          <p
            className={`agent-operational agent-operational--${overview.operational_status}`}
          >
            {operationalMessage(overview.operational_message)}
          </p>
          {overview.operational_status === 'unavailable' &&
            aiErrorHint(overview.operational_message) && (
              <p className="ai-error-hint">
                {aiErrorHint(overview.operational_message)}
              </p>
            )}
        </div>
      </section>
      <section className="workflow-panel">
        <h2>Configuração do workspace</h2>
        <div className="agent-config-grid">
          <label>
            <span>Ativo</span>
            <input
              type="checkbox"
              checked={overview.configuration.enabled}
              disabled={saving}
              onChange={async (event) => {
                setSaving(true);
                setMessage('');
                try {
                  await updateAgentConfiguration(id, {
                    enabled: event.target.checked,
                  });
                  setOverview(await getAgentOverview(id));
                  setMessage('Configuração guardada.');
                } catch {
                  setMessage(
                    'Só os administradores do workspace podem alterar esta configuração.',
                  );
                } finally {
                  setSaving(false);
                }
              }}
            />
          </label>
          <label>
            Política de aprovação
            <select
              value={overview.configuration.approval_policy}
              disabled={saving}
              onChange={async (event) => {
                setSaving(true);
                setMessage('');
                try {
                  await updateAgentConfiguration(id, {
                    approval_policy: event.target
                      .value as AgentOverview['configuration']['approval_policy'],
                  });
                  setOverview(await getAgentOverview(id));
                  setMessage('Configuração guardada.');
                } catch {
                  setMessage('Não foi possível guardar a configuração.');
                } finally {
                  setSaving(false);
                }
              }}
            >
              <option value="platform_default">
                Predefinição da plataforma
              </option>
              <option value="risk_based">Com base no risco</option>
              <option value="always">Pedir sempre aprovação</option>
            </select>
          </label>
        </div>
        {message && (
          <p className="form-message" role="status">
            {message}
          </p>
        )}
      </section>
      <section className="workflow-panel">
        <h2>Capacidades</h2>
        <p>Máximo de {overview.capabilities.max_actions} ações por tarefa</p>
        <div className="tool-chips">
          {overview.capabilities.allowed_tools.map((tool) => (
            <code key={tool}>{tool}</code>
          ))}
        </div>
      </section>
      <section className="workflow-panel">
        <h2>Recent runs · {overview.success_rate}% success</h2>
        {overview.recent_runs.map((run) => (
          <div className="action-row" key={run.id}>
            <div>
              <strong>
                {run.proposal_summary ??
                  run.error_message ??
                  'Execução do agente'}
              </strong>
              <span>
                {' '}
                · {run.model} · {run.total_tokens ?? 0} tokens
              </span>
            </div>
            <StatusBadge status={run.status} />
          </div>
        ))}
      </section>
    </main>
  );
}
