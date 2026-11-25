'use client';

import type {
  AuditLog,
  TaskAction,
  TaskDetail,
  TaskExecution,
} from '@agent/shared';
import React, { useCallback, useEffect, useState } from 'react';

import {
  createTaskAction,
  dispatchAction,
  listActionExecutions,
  listCommandActivity,
  listTaskActions,
  WorkflowApiError,
} from '../lib/workflow-client';
import { StatusBadge } from './status-badge';
import { CanEdit } from '../lib/workspace-access';
import { label } from '../lib/labels';
import { apiMessage } from '../lib/api-messages';

const TOOLS = [
  'internal.echo',
  'internal.summarize',
  'internal.create_note',
  'internal.simulate_external_action',
  'internal.simulate_critical_action',
];

export function TaskExecutionPanel({
  commandId,
  tasks,
}: {
  commandId: string;
  tasks: TaskDetail[];
}) {
  const [actions, setActions] = useState<Record<string, TaskAction[]>>({});
  const [executions, setExecutions] = useState<Record<string, TaskExecution[]>>(
    {},
  );
  const [activity, setActivity] = useState<AuditLog[]>([]);
  const [tool, setTool] = useState<Record<string, string>>({});
  const [text, setText] = useState<Record<string, string>>({});
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const loaded = await Promise.all(
      tasks.map(
        async (task) => [task.id, await listTaskActions(task.id)] as const,
      ),
    );
    const actionMap = Object.fromEntries(loaded);
    const allActions = loaded.flatMap(([, items]) => items);
    const executionPairs = await Promise.all(
      allActions.map(
        async (action) =>
          [action.id, await listActionExecutions(action.id)] as const,
      ),
    );
    setActions(actionMap);
    setExecutions(Object.fromEntries(executionPairs));
    setActivity(await listCommandActivity(commandId));
  }, [commandId, tasks]);

  useEffect(() => {
    void load().catch((loadError) =>
      setError(
        loadError instanceof WorkflowApiError
          ? loadError.message
          : 'Não foi possível carregar a atividade de execução.',
      ),
    );
  }, [load]);

  async function createAndDispatch(task: TaskDetail) {
    const selected = tool[task.id] ?? 'internal.echo';
    const description = text[task.id]?.trim();
    if (!description) return;
    const inputPayload = selected.includes('simulate')
      ? { action: selected.split('.').at(-1), description }
      : { text: description };
    try {
      const action = await createTaskAction(task.id, {
        tool_name: selected,
        input_payload: inputPayload,
      });
      await dispatchAction(action.id);
      setText((current) => ({ ...current, [task.id]: '' }));
      await load();
    } catch (submitError) {
      setError(
        submitError instanceof WorkflowApiError
          ? submitError.message
          : 'Não foi possível enviar a ação.',
      );
    }
  }

  return (
    <section className="execution-workbench">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Motor de execução</p>
          <h2>Ações e tentativas</h2>
        </div>
      </div>
      {error && <p className="workflow-alert">{error}</p>}
      {tasks.map((task) => (
        <article className="workflow-panel" key={task.id}>
          <div className="workflow-panel__heading">
            <h3>{task.title}</h3>
            <StatusBadge status={task.status} />
          </div>
          <CanEdit>
            {task.status === 'ready' && (
              <div className="action-composer">
                <select
                  aria-label="Ferramenta"
                  value={tool[task.id] ?? TOOLS[0]}
                  onChange={(event) =>
                    setTool((current) => ({
                      ...current,
                      [task.id]: event.target.value,
                    }))
                  }
                >
                  {TOOLS.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
                <input
                  aria-label="Dados da ação"
                  placeholder="Texto ou descrição da ação simulada"
                  value={text[task.id] ?? ''}
                  onChange={(event) =>
                    setText((current) => ({
                      ...current,
                      [task.id]: event.target.value,
                    }))
                  }
                />
                <button
                  className="primary-button"
                  type="button"
                  onClick={() => void createAndDispatch(task)}
                >
                  Criar e enviar
                </button>
              </div>
            )}
          </CanEdit>
          {(actions[task.id] ?? []).map((action) => (
            <div className="action-row" key={action.id}>
              <div>
                <strong>{action.tool_name}</strong>
                <span> · {label(action.risk_level)}</span>
              </div>
              <StatusBadge status={action.status} />
              <ol className="attempt-list">
                {(executions[action.id] ?? []).map((execution) => (
                  <li key={execution.id}>
                    Attempt {execution.attempt_number} —{' '}
                    {label(execution.status)}
                    {execution.duration_ms !== null
                      ? ` · ${execution.duration_ms}ms`
                      : ''}
                    {execution.error_message
                      ? ` · ${apiMessage(execution.error_message)}`
                      : ''}
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </article>
      ))}
      <details className="workflow-panel activity-timeline">
        <summary>Activity timeline ({activity.length})</summary>
        <ol>
          {activity.map((entry) => (
            <li key={entry.id}>
              <time>
                {new Date(entry.created_at).toLocaleTimeString('pt-PT')}
              </time>
              <strong>{label(entry.event_type)}</strong>
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}
