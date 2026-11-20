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
    void load().catch(() => setError('Unable to load agent runs.'));
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
                : 'Unable to follow the agent run.',
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
          : 'Unable to run agent.',
      );
    } finally {
      setStarting('');
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
                <span className="eyebrow">Assigned Agent</span>
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
                      ? 'Analyzing…'
                      : latest
                        ? 'Run agent again'
                        : 'Ask agent to prepare actions'}
                  </button>
                  {latest && !working && (
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
  'github.create_issue': 'Create GitHub Issue',
  'github.comment_issue': 'Comment on GitHub Issue',
  'github.create_branch': 'Create GitHub Branch',
  'github.create_or_update_file': 'Create or Update GitHub File',
  'github.open_pull_request': 'Open GitHub Pull Request',
  'email.send': 'Send Email',
  'email.reply': 'Reply to Email',
  'email.mark_read': 'Mark Email Read',
  'calendar.create_event': 'Create Calendar Event',
  'calendar.update_event': 'Update Calendar Event',
  'calendar.cancel_event': 'Cancel Calendar Event',
  'marketing.create_campaign': 'Create Marketing Campaign',
  'marketing.update_campaign': 'Update Marketing Campaign',
  'marketing.create_content': 'Create Content Draft',
  'marketing.update_content': 'Update Content Draft',
  'marketing.transition_content': 'Transition Content Lifecycle',
  'marketing.schedule_content': 'Schedule Proposed Content',
  'marketing.record_publication': 'Record Confirmed Publication',
  'marketing.add_asset_metadata': 'Add Asset Metadata',
  'marketing.record_metric': 'Record Performance Metric',
  'crm.create_client': 'Create Client Profile',
  'crm.update_client': 'Update Client Profile',
  'crm.create_project': 'Create Client Project',
  'crm.update_project': 'Update Client Project',
  'crm.create_pipeline': 'Create Sales Pipeline',
  'crm.create_opportunity': 'Create Opportunity',
  'crm.update_opportunity': 'Update Opportunity',
  'crm.link_task': 'Link Task to Client',
  'crm.create_organization': 'Create CRM Organization',
  'crm.create_contact': 'Create CRM Contact',
  'crm.update_contact': 'Update CRM Contact',
  'crm.add_note': 'Add CRM Note',
  'crm.link_email': 'Link Email to CRM',
  'crm.link_event': 'Link Event to CRM',
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
        <span>Repository: {repository}</span>
      )}
      {github && typeof title === 'string' && <span>Title: {title}</span>}
      {github && typeof branch === 'string' && <span>Branch: {branch}</span>}
      {email && typeof account === 'string' && <span>Account: {account}</span>}
      {email && typeof subject === 'string' && <span>Subject: {subject}</span>}
      {email && recipients && <span>Recipients: {recipients}</span>}
      {calendar && typeof account === 'string' && (
        <span>Account: {account}</span>
      )}
      {calendar && typeof calendarId === 'string' && (
        <span>Calendar: {calendarId}</span>
      )}
      {calendar && typeof eventId === 'string' && <span>Event: {eventId}</span>}
      {calendar && typeof title === 'string' && <span>Title: {title}</span>}
      {calendar && start !== undefined && (
        <span>Start: {JSON.stringify(start)}</span>
      )}
      {calendar && end !== undefined && <span>End: {JSON.stringify(end)}</span>}
      {calendar && typeof location === 'string' && (
        <span>Location: {location}</span>
      )}
      {calendar && attendees && <span>Attendees: {attendees}</span>}
      {(crm || marketing) && (
        <span>Exact payload: {JSON.stringify(action.input_payload)}</span>
      )}
      <span>Risk: {action.risk_level}</span>
      {(github || email || calendar || crm || marketing) && (
        <span>
          Requires approval: {action.risk_level === 'green' ? 'No' : 'Yes'}
        </span>
      )}
      <StatusBadge status={action.status} />
    </li>
  );
}
