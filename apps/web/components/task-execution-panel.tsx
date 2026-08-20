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
          : 'Unable to load execution activity.',
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
          : 'Unable to dispatch action.',
      );
    }
  }

  return (
    <section className="execution-workbench">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Execution Engine</p>
          <h2>Actions and attempts</h2>
        </div>
      </div>
      {error && <p className="workflow-alert">{error}</p>}
      {tasks.map((task) => (
        <article className="workflow-panel" key={task.id}>
          <div className="workflow-panel__heading">
            <h3>{task.title}</h3>
            <StatusBadge status={task.status} />
          </div>
          {task.status === 'ready' && (
            <div className="action-composer">
              <select
                value={tool[task.id] ?? TOOLS[0]}
                onChange={(event) =>
                  setTool((current) => ({
                    ...current,
                    [task.id]: event.target.value,
                  }))
                }
              >
                {TOOLS.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
              <input
                placeholder="Text or simulated action description"
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
                Create & dispatch
              </button>
            </div>
          )}
          {(actions[task.id] ?? []).map((action) => (
            <div className="action-row" key={action.id}>
              <div>
                <strong>{action.tool_name}</strong>
                <span> · {action.risk_level}</span>
              </div>
              <StatusBadge status={action.status} />
              <ol className="attempt-list">
                {(executions[action.id] ?? []).map((execution) => (
                  <li key={execution.id}>
                    Attempt {execution.attempt_number} — {execution.status}
                    {execution.duration_ms !== null
                      ? ` · ${execution.duration_ms}ms`
                      : ''}
                    {execution.error_message
                      ? ` · ${execution.error_message}`
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
              <time>{new Date(entry.created_at).toLocaleTimeString()}</time>
              <strong>{entry.event_type.replaceAll('_', ' ')}</strong>
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}
