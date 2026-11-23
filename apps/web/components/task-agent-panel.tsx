'use client';

import type { AgentRun, TaskAction, TaskDetail } from '@agent/shared';
import React, { useCallback, useEffect, useRef, useState } from 'react';

import {
  isAgentRunActive,
  listAgentRuns,
  listTaskActions,
  startAgentRun,
  waitForAgentRun,
  WorkflowApiError,
} from '../lib/workflow-client';
import { AiErrorNotice } from './ai-error-notice';
import { AiProgress } from './ai-progress';
import { StatusBadge } from './status-badge';
import { CanEdit } from '../lib/workspace-access';
import { label } from '../lib/labels';

/**
 * Agents run in the background: starting one answers at once, the panel follows the run
 * (also after the page is left and opened again) and shows the proposed actions when it
 * finishes. `onFinished` lets the page reload what the run changed.
 */
export function TaskAgentPanel({
  tasks,
  onFinished,
}: {
  tasks: TaskDetail[];
  onFinished?: () => void;
}) {
  const [runs, setRuns] = useState<Record<string, AgentRun[]>>({});
  const [proposals, setProposals] = useState<Record<string, TaskAction[]>>({});
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [starting, setStarting] = useState('');
  const [error, setError] = useState('');
  // Kept in a ref so a new callback from the page does not restart the pollers.
  const finishedRef = useRef(onFinished);
  finishedRef.current = onFinished;

  const load = useCallback(async () => {
    const pairs = await Promise.all(
      tasks.map(
        async (task) => [task.id, await listAgentRuns(task.id)] as const,
      ),
    );
    setRuns(Object.fromEntries(pairs));
  }, [tasks]);

  useEffect(() => {
    void load().catch(() =>
      setError('Não foi possível carregar as execuções dos agentes.'),
    );
  }, [load]);

  // Follow every run that is still working, one poller per run.
  const activeKey = Object.entries(runs)
    .map(([taskId, history]) =>
      history[0] && isAgentRunActive(history[0])
        ? `${taskId}:${history[0].id}`
        : '',
    )
    .filter(Boolean)
    .join(',');

  useEffect(() => {
    if (!activeKey) return;
    let cancelled = false;
    for (const pair of activeKey.split(',')) {
      const [taskId, runId] = pair.split(':');
      void waitForAgentRun(taskId, runId, { isCancelled: () => cancelled })
        .then(async (finished) => {
          if (cancelled || !finished) return;
          if (finished.status === 'completed') {
            const actions = await listTaskActions(taskId);
            setProposals((current) => ({
              ...current,
              [taskId]: actions.filter(
                (action) =>
                  Date.parse(action.created_at) >=
                  Date.parse(finished.created_at),
              ),
            }));
          } else if (finished.error_message) {
            setError(finished.error_message);
          }
          await load();
          finishedRef.current?.();
        })
        .catch((pollError) => {
          if (!cancelled)
            setError(
              pollError instanceof WorkflowApiError
                ? pollError.message
                : 'Não foi possível acompanhar a execução do agente.',
            );
        });
    }
    return () => {
      cancelled = true;
    };
  }, [activeKey, load]);

  async function execute(task: TaskDetail) {
    setStarting(task.id);
    setError('');
    try {
      const run = await startAgentRun(task.id, feedback[task.id] || undefined);
      setFeedback((current) => ({ ...current, [task.id]: '' }));
      setProposals((current) => ({ ...current, [task.id]: [] }));
      setRuns((current) => ({
        ...current,
        [task.id]: [run, ...(current[task.id] ?? [])],
      }));
    } catch (runError) {
      setError(
        runError instanceof WorkflowApiError
          ? runError.message
          : 'Não foi possível executar o agente.',
      );
    } finally {
      setStarting('');
    }
  }

  return (
    <section className="execution-workbench">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Agentes especializados</p>
          <h2>Análise dos agentes e propostas de ação</h2>
        </div>
      </div>
      {error && <AiErrorNotice message={error} />}
      {tasks.map((task) => {
        const history = runs[task.id] ?? [];
        const latest = history[0];
        const working = Boolean(latest && isAgentRunActive(latest));
        const busy = working || starting === task.id;
        const actions = proposals[task.id] ?? [];
        return (
          <article className="workflow-panel agent-run-card" key={task.id}>
            <div className="workflow-panel__heading">
              <div>
                <span className="eyebrow">Agente atribuído</span>
                <h3>{task.agent_id}</h3>
                <p>{task.title}</p>
              </div>
              {latest && <StatusBadge status={latest.status} />}
            </div>
            <CanEdit>
              {task.status === 'ready' && (
                <div className="agent-run-controls">
                  <button
                    className="primary-button"
                    disabled={busy}
                    onClick={() => void execute(task)}
                    type="button"
                  >
                    {busy
                      ? 'A analisar…'
                      : latest
                        ? 'Executar o agente de novo'
                        : 'Pedir ao agente que prepare ações'}
                  </button>
                  {latest && !working && (
                    <input
                      maxLength={5000}
                      placeholder="Comentário opcional"
                      value={feedback[task.id] ?? ''}
                      onChange={(event) =>
                        setFeedback((current) => ({
                          ...current,
                          [task.id]: event.target.value,
                        }))
                      }
                    />
                  )}
                </div>
              )}
            </CanEdit>
            {working && latest && (
              <AiProgress
                since={Date.parse(latest.created_at)}
                label="O agente está a analisar a tarefa…"
                canLeave
              />
            )}
            {latest && !working && (
              <dl className="execution-meta">
                <div>
                  <dt>Modelo</dt>
                  <dd>{latest.model}</dd>
                </div>
                <div>
                  <dt>Tokens</dt>
                  <dd>{latest.total_tokens ?? '—'}</dd>
                </div>
                <div>
                  <dt>Duração</dt>
                  <dd>{latest.latency_ms ?? '—'} ms</dd>
                </div>
                <div>
                  <dt>Resumo</dt>
                  <dd>
                    {latest.proposal_summary ?? latest.error_message ?? '—'}
                  </dd>
                </div>
              </dl>
            )}
            {actions.length > 0 && (
              <ol className="proposal-preview">
                {actions.map((action) => (
                  <ActionProposalPreview action={action} key={action.id} />
                ))}
              </ol>
            )}
          </article>
        );
      })}
    </section>
  );
}

const ACTION_LABELS: Record<string, string> = {
  'github.create_issue': 'Criar issue no GitHub',
  'github.comment_issue': 'Comentar issue do GitHub',
  'github.create_branch': 'Criar branch no GitHub',
  'github.create_or_update_file': 'Criar ou atualizar ficheiro no GitHub',
  'github.open_pull_request': 'Abrir pull request no GitHub',
  'email.send': 'Enviar email',
  'email.reply': 'Responder a email',
  'email.mark_read': 'Marcar email como lido',
  'calendar.create_event': 'Criar evento de calendário',
  'calendar.update_event': 'Atualizar evento de calendário',
  'calendar.cancel_event': 'Cancelar evento de calendário',
  'marketing.create_campaign': 'Criar campanha de marketing',
  'marketing.update_campaign': 'Atualizar campanha de marketing',
  'marketing.create_content': 'Criar rascunho de conteúdo',
  'marketing.update_content': 'Atualizar rascunho de conteúdo',
  'marketing.transition_content': 'Mudar estado do conteúdo',
  'marketing.schedule_content': 'Agendar conteúdo proposto',
  'marketing.record_publication': 'Registar publicação confirmada',
  'marketing.add_asset_metadata': 'Adicionar metadados do recurso',
  'marketing.record_metric': 'Registar métrica de desempenho',
  'crm.create_client': 'Criar perfil de cliente',
  'crm.update_client': 'Atualizar perfil de cliente',
  'crm.create_project': 'Criar projeto de cliente',
  'crm.update_project': 'Atualizar projeto de cliente',
  'crm.create_pipeline': 'Criar pipeline de vendas',
  'crm.create_opportunity': 'Criar oportunidade',
  'crm.update_opportunity': 'Atualizar oportunidade',
  'crm.link_task': 'Ligar tarefa a cliente',
  'crm.create_organization': 'Criar organização no CRM',
  'crm.create_contact': 'Criar contacto no CRM',
  'crm.update_contact': 'Atualizar contacto no CRM',
  'crm.add_note': 'Adicionar nota no CRM',
  'crm.link_email': 'Ligar email ao CRM',
  'crm.link_event': 'Ligar evento ao CRM',
};

export function ActionProposalPreview({ action }: { action: TaskAction }) {
  const github = action.tool_name.startsWith('github.');
  const email = action.tool_name.startsWith('email.');
  const calendar = action.tool_name.startsWith('calendar.');
  const crm = action.tool_name.startsWith('crm.');
  const marketing = action.tool_name.startsWith('marketing.');
  const repository = action.input_payload.repository;
  const title = action.input_payload.title;
  const account = action.input_payload.account_id;
  const subject = action.input_payload.subject;
  const calendarId = action.input_payload.calendar_id;
  const eventId = action.input_payload.event_id;
  const start = action.input_payload.start;
  const end = action.input_payload.end;
  const location = action.input_payload.location;
  const attendees = Array.isArray(action.input_payload.attendees)
    ? action.input_payload.attendees.map(String).join(', ')
    : '';
  const recipients = Array.isArray(action.input_payload.to)
    ? action.input_payload.to
        .map((value) =>
          typeof value === 'object' && value && 'address' in value
            ? String(value.address)
            : '',
        )
        .filter(Boolean)
        .join(', ')
    : '';
  const branch =
    action.input_payload.branch ??
    action.input_payload.head ??
    action.input_payload.ref;

  return (
    <li>
      <strong>{ACTION_LABELS[action.tool_name] ?? action.tool_name}</strong>
      {github && typeof repository === 'string' && (
        <span>Repositório: {repository}</span>
      )}
      {github && typeof title === 'string' && <span>Título: {title}</span>}
      {github && typeof branch === 'string' && <span>Branch: {branch}</span>}
      {email && typeof account === 'string' && <span>Conta: {account}</span>}
      {email && typeof subject === 'string' && <span>Assunto: {subject}</span>}
      {email && recipients && <span>Destinatários: {recipients}</span>}
      {calendar && typeof account === 'string' && <span>Conta: {account}</span>}
      {calendar && typeof calendarId === 'string' && (
        <span>Calendário: {calendarId}</span>
      )}
      {calendar && typeof eventId === 'string' && (
        <span>Evento: {eventId}</span>
      )}
      {calendar && typeof title === 'string' && <span>Título: {title}</span>}
      {calendar && start !== undefined && (
        <span>Início: {JSON.stringify(start)}</span>
      )}
      {calendar && end !== undefined && <span>Fim: {JSON.stringify(end)}</span>}
      {calendar && typeof location === 'string' && (
        <span>Local: {location}</span>
      )}
      {calendar && attendees && <span>Participantes: {attendees}</span>}
      {(crm || marketing) && (
        <span>Dados exatos: {JSON.stringify(action.input_payload)}</span>
      )}
      <span>Risco: {label(action.risk_level)}</span>
      {(github || email || calendar || crm || marketing) && (
        <span>
          Requer aprovação: {action.risk_level === 'green' ? 'Não' : 'Sim'}
        </span>
      )}
      <StatusBadge status={action.status} />
    </li>
  );
}
