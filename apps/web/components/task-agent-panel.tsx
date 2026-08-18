'use client';

import type { AgentRun, TaskAction, TaskDetail } from '@agent/shared';
import React, { useCallback, useEffect, useState } from 'react';

import {
  listAgentRuns,
  rerunAgent,
  runAgent,
  WorkflowApiError,
} from '../lib/workflow-client';
import { StatusBadge } from './status-badge';

export function TaskAgentPanel({ tasks }: { tasks: TaskDetail[] }) {
  const [runs, setRuns] = useState<Record<string, AgentRun[]>>({});
  const [proposals, setProposals] = useState<Record<string, TaskAction[]>>({});
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const pairs = await Promise.all(
      tasks.map(
        async (task) => [task.id, await listAgentRuns(task.id)] as const,
      ),
    );
    setRuns(Object.fromEntries(pairs));
  }, [tasks]);

  useEffect(() => {
    void load().catch(() => setError('Unable to load agent runs.'));
  }, [load]);

  async function execute(task: TaskDetail, isRerun: boolean) {
    setBusy(task.id);
    setError('');
    try {
      const result = isRerun
        ? await rerunAgent(task.id, feedback[task.id] || undefined)
        : await runAgent(task.id);
      setProposals((current) => ({ ...current, [task.id]: result.actions }));
      setFeedback((current) => ({ ...current, [task.id]: '' }));
      await load();
    } catch (runError) {
      setError(
        runError instanceof WorkflowApiError
          ? runError.message
          : 'Unable to run agent.',
      );
    } finally {
      setBusy('');
    }
  }

  return (
    <section className="execution-workbench">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Specialized agents</p>
          <h2>Agent analysis and action proposals</h2>
        </div>
      </div>
      {error && <p className="workflow-alert">{error}</p>}
      {tasks.map((task) => {
        const history = runs[task.id] ?? [];
        const latest = history[0];
        const actions = proposals[task.id] ?? [];
        return (
          <article className="workflow-panel agent-run-card" key={task.id}>
            <div className="workflow-panel__heading">
              <div>
                <span className="eyebrow">Assigned Agent</span>
                <h3>{task.agent_id}</h3>
                <p>{task.title}</p>
              </div>
              {latest && <StatusBadge status={latest.status} />}
            </div>
            {task.status === 'ready' && (
              <div className="agent-run-controls">
                <button
                  className="primary-button"
                  disabled={busy === task.id}
                  onClick={() => void execute(task, Boolean(latest))}
                  type="button"
                >
                  {busy === task.id
                    ? 'Analyzing…'
                    : latest
                      ? 'Run agent again'
                      : 'Ask agent to prepare actions'}
                </button>
                {latest && (
                  <input
                    maxLength={5000}
                    placeholder="Optional feedback"
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
            {latest && (
              <dl className="execution-meta">
                <div>
                  <dt>Model</dt>
                  <dd>{latest.model}</dd>
                </div>
                <div>
                  <dt>Tokens</dt>
                  <dd>{latest.total_tokens ?? '—'}</dd>
                </div>
                <div>
                  <dt>Duration</dt>
                  <dd>{latest.latency_ms ?? '—'} ms</dd>
                </div>
                <div>
                  <dt>Summary</dt>
                  <dd>
                    {latest.proposal_summary ?? latest.error_message ?? '—'}
                  </dd>
                </div>
              </dl>
            )}
            {actions.length > 0 && (
              <ol className="proposal-preview">
                {actions.map((action) => (
                  <li key={action.id}>
                    <strong>{action.tool_name}</strong>
                    <span>Risk: {action.risk_level}</span>
                    <StatusBadge status={action.status} />
                  </li>
                ))}
              </ol>
            )}
          </article>
        );
      })}
    </section>
  );
}
