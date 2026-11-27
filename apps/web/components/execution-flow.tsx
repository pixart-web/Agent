'use client';

import React, { useEffect, useMemo, useState } from 'react';

import { apiMessage, failureMessage } from '../lib/api-messages';
import { label, serverText } from '../lib/labels';
import {
  getExecutionGraph,
  type ExecutionGraph,
  type ExecutionGraphNode,
  type ExecutionGraphStep,
} from '../lib/workflow-client';
import { StatusBadge } from './status-badge';

const STEP_KIND: Record<ExecutionGraphStep['kind'], string> = {
  status: 'Estado',
  agent_run: 'Agente',
  execution: 'Execução',
};

function formatDuration(ms: number | null): string | null {
  if (ms === null) return null;
  if (ms < 1000) return `${ms} ms`;
  const seconds = ms / 1000;
  return seconds < 60
    ? `${seconds.toFixed(1).replace('.', ',')} s`
    : `${Math.round(seconds / 60)} min`;
}

function stepSummary(step: ExecutionGraphStep): string {
  if (step.kind === 'status') {
    return step.detail
      ? `${label(step.detail)} → ${label(step.status)}`
      : label(step.status);
  }
  if (step.kind === 'agent_run')
    return `${label(step.title)} · ${label(step.status)}`;
  return `${step.title} ${step.detail ?? ''} · ${label(step.status)}`;
}

function StepLog({ node }: { node: ExecutionGraphNode }) {
  if (node.steps.length === 0) {
    return <p className="empty-state">Ainda não há passos registados.</p>;
  }
  return (
    <ol className="flow-log">
      {node.steps.map((step, index) => {
        const duration = formatDuration(step.duration_ms);
        return (
          <li
            key={`${step.kind}-${step.at}-${index}`}
            className={`flow-log__item flow-log__item--${step.kind}`}
          >
            <time dateTime={step.at}>
              {new Date(step.at).toLocaleString('pt-PT')}
            </time>
            <span className="flow-log__kind">{STEP_KIND[step.kind]}</span>
            <span className="flow-log__text">
              {stepSummary(step)}
              {duration ? ` · ${duration}` : ''}
            </span>
            {step.note ? (
              <span className="flow-log__detail">{serverText(step.note)}</span>
            ) : null}
            {step.error_message ? (
              <span className="flow-log__error">
                {apiMessage(step.error_message)}
              </span>
            ) : null}
            {step.kind === 'agent_run' && step.detail ? (
              <span className="flow-log__detail">{step.detail}</span>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

/** Dependency graph of a plan's tasks, by stage, with each task's step log. */
export function ExecutionFlow({
  planId,
  refreshKey,
}: {
  planId: string;
  refreshKey: string;
}) {
  const [graph, setGraph] = useState<ExecutionGraph | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    getExecutionGraph(planId)
      .then((loaded) => {
        if (!active) return;
        setGraph(loaded);
        setError('');
      })
      .catch((failure) => {
        if (active)
          setError(
            failureMessage(failure, 'Não foi possível carregar o fluxo.'),
          );
      });
    return () => {
      active = false;
    };
  }, [planId, refreshKey]);

  const stages = useMemo(() => {
    if (!graph) return [];
    return Array.from({ length: graph.levels }, (_, level) =>
      graph.nodes.filter((node) => node.level === level),
    );
  }, [graph]);
  const titles = useMemo(
    () => new Map(graph?.nodes.map((node) => [node.task_id, node.title]) ?? []),
    [graph],
  );
  const current = graph?.nodes.find((node) => node.task_id === selected);

  if (error) return <p className="workflow-alert">{error}</p>;
  if (!graph || graph.nodes.length === 0) return null;

  return (
    <section className="flow-panel" aria-labelledby="flow-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Fluxo de execução</p>
          <h2 id="flow-title">Dependências e passos</h2>
        </div>
      </div>
      <div className="flow-stages" role="list">
        {stages.map((nodes, level) => (
          <div className="flow-stage" role="listitem" key={level}>
            <p className="flow-stage__label">Etapa {level + 1}</p>
            {nodes.map((node) => (
              <button
                key={node.task_id}
                type="button"
                className={`flow-node flow-node--${node.status}${
                  selected === node.task_id ? ' flow-node--selected' : ''
                }`}
                aria-pressed={selected === node.task_id}
                onClick={() =>
                  setSelected((value) =>
                    value === node.task_id ? null : node.task_id,
                  )
                }
              >
                <span className="flow-node__title">{node.title}</span>
                <StatusBadge status={node.status} />
                <span className="flow-node__meta">
                  {label(node.agent_id)} · risco{' '}
                  {label(node.risk_level).toLowerCase()}
                </span>
                {node.depends_on.length > 0 ? (
                  <span className="flow-node__deps">
                    Depois de:{' '}
                    {node.depends_on
                      .map((id) => titles.get(id) ?? 'outra tarefa')
                      .join(', ')}
                  </span>
                ) : null}
              </button>
            ))}
          </div>
        ))}
      </div>
      {current ? (
        <div className="flow-detail" aria-live="polite">
          <h3>Passos de “{current.title}”</h3>
          <StepLog node={current} />
        </div>
      ) : (
        <p className="form-hint">
          Escolhe uma tarefa para ver o registo dos seus passos.
        </p>
      )}
    </section>
  );
}
