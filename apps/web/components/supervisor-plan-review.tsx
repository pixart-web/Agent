import type { Plan, SupervisorRun, WorkflowTask } from '@agent/shared';
import React from 'react';

import type { Agent } from '../lib/workflow-client';
import { StatusBadge } from './status-badge';

type Props = {
  plan: Plan | null;
  tasks: WorkflowTask[];
  versions: Plan[];
  run: SupervisorRun | null;
  agents: Agent[];
  planning: boolean;
  error: string;
  feedback: string;
  onFeedbackChange: (value: string) => void;
  onGenerate: () => void;
  onApprove: () => void;
  onRegenerate: () => void;
};

export function SupervisorPlanReview({
  plan,
  tasks,
  versions,
  run,
  agents,
  planning,
  error,
  feedback,
  onFeedbackChange,
  onGenerate,
  onApprove,
  onRegenerate,
}: Props) {
  const agentNames = Object.fromEntries(
    agents.map((agent) => [agent.id, agent.name]),
  );

  if (!plan) {
    return (
      <section className="workflow-panel supervisor-panel">
        <p className="eyebrow">Pixart AI Supervisor</p>
        <h2>Transforma o pedido num plano revisto por humanos</h2>
        <p>
          O Supervisor propõe tarefas e classifica prioridade e risco. Não
          executa qualquer ação externa.
        </p>
        {error && <p role="alert">{error}</p>}
        <button
          className="primary-button"
          type="button"
          disabled={planning}
          onClick={onGenerate}
        >
          {planning
            ? 'Supervisor está a preparar o plano…'
            : 'Gerar plano com Supervisor'}
        </button>
      </section>
    );
  }

  return (
    <section className="workflow-panel supervisor-panel" id={`plan-${plan.id}`}>
      <div className="workflow-panel__heading">
        <div>
          <p className="eyebrow">
            Plano proposto pelo Supervisor · v{plan.version}
          </p>
          <h2>{plan.title}</h2>
        </div>
        <StatusBadge status={plan.status} />
      </div>
      <h3>Objetivo</h3>
      <p>{plan.objective}</p>
      {plan.reasoning_summary && (
        <p className="reasoning-summary">{plan.reasoning_summary}</p>
      )}

      <div className="supervisor-task-list">
        {tasks.map((task) => (
          <article className="task-card" key={task.id}>
            <span className="task-sequence">#{task.sequence}</span>
            <h3>
              {agentNames[task.agent_id] ?? task.agent_id} — {task.title}
            </h3>
            <p>{task.instructions}</p>
            <p className="supervisor-task-meta">
              Prioridade: {task.priority} · Risco: {task.risk_level}
            </p>
          </article>
        ))}
      </div>

      {run && (
        <dl className="supervisor-run-meta">
          <div>
            <dt>Modelo</dt>
            <dd>{run.model}</dd>
          </div>
          <div>
            <dt>Tokens utilizados</dt>
            <dd>{run.total_tokens ?? 'indisponível'}</dd>
          </div>
          <div>
            <dt>Latência</dt>
            <dd>
              {run.latency_ms === null
                ? 'indisponível'
                : `${run.latency_ms} ms`}
            </dd>
          </div>
        </dl>
      )}

      {plan.is_current && plan.status === 'draft' && (
        <div className="supervisor-review-actions">
          <button
            className="primary-button"
            type="button"
            disabled={planning}
            onClick={onApprove}
          >
            Aprovar plano
          </button>
          <label>
            O que queres alterar?
            <textarea
              rows={4}
              maxLength={5000}
              value={feedback}
              onChange={(event) => onFeedbackChange(event.target.value)}
            />
          </label>
          <button
            className="secondary-button"
            type="button"
            disabled={planning || !feedback.trim()}
            onClick={onRegenerate}
          >
            {planning ? 'A replanear…' : 'Pedir alterações'}
          </button>
        </div>
      )}

      {error && <p role="alert">{error}</p>}

      {versions.length > 0 && (
        <details className="plan-history">
          <summary>Histórico de versões ({versions.length})</summary>
          <ol>
            {versions.map((version) => (
              <li key={version.id}>
                <strong>Plan v{version.version}</strong> —{' '}
                {version.is_current ? 'current' : version.status}
                <p>{version.title}</p>
                {version.rejection_reason && (
                  <p>Motivo: {version.rejection_reason}</p>
                )}
              </li>
            ))}
          </ol>
        </details>
      )}
    </section>
  );
}
