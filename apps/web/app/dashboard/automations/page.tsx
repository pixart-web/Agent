'use client';

import type { Automation, AutomationRun } from '@agent/shared';
import { FormEvent, useCallback, useEffect, useState } from 'react';

import {
  AutomationPolicyNote,
  AutomationRunSummary,
} from '../../../components/automation-summary';
import { DashboardNav } from '../../../components/dashboard-nav';
import {
  createAutomation,
  listAutomationRuns,
  listAutomations,
  recoverAutomationRun,
  setAutomationEnabled,
  triggerManualAutomation,
  updateAutomation,
} from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function AutomationsPage() {
  const { user, loading } = useAuthenticatedUser();
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [name, setName] = useState('');
  const [commandTemplate, setCommandTemplate] = useState('');
  const [triggerType, setTriggerType] =
    useState<Automation['trigger_type']>('manual');
  const [triggerValue, setTriggerValue] = useState('');
  const [conditionField, setConditionField] = useState('');
  const [conditionValue, setConditionValue] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [automationValue, runValue] = await Promise.all([
      listAutomations(),
      listAutomationRuns(),
    ]);
    setAutomations(automationValue.automations);
    setRuns(runValue.runs);
  }, []);

  useEffect(() => {
    if (user)
      void refresh().catch(() => setError('Unable to load automations.'));
  }, [refresh, user]);

  async function act(operation: () => Promise<unknown>, message: string) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await operation();
      await refresh();
      setNotice(message);
    } catch {
      setError('The governed automation operation could not be completed.');
    } finally {
      setBusy(false);
    }
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const triggerConfig: Record<string, unknown> = {};
    let nextRunAt: string | undefined;
    if (triggerType === 'schedule') {
      triggerConfig.interval_minutes = Number(triggerValue);
      nextRunAt = new Date(
        Date.now() + Number(triggerValue) * 60_000,
      ).toISOString();
    } else if (triggerType === 'email_received') {
      triggerConfig.account_id = triggerValue;
    } else if (triggerType === 'calendar_event') {
      const [accountId, calendarId] = triggerValue
        .split(',')
        .map((value) => value.trim());
      triggerConfig.account_id = accountId;
      triggerConfig.calendar_id = calendarId;
    } else if (triggerType === 'webhook') {
      triggerConfig.source = triggerValue;
    } else if (triggerType === 'crm_change') {
      triggerConfig.entity_types = triggerValue
        .split(',')
        .map((value) => value.trim());
      triggerConfig.change_types = ['created', 'updated'];
    } else if (triggerType === 'task_state') {
      triggerConfig.statuses = triggerValue
        .split(',')
        .map((value) => value.trim());
    }
    await act(
      () =>
        createAutomation({
          name: name.trim(),
          command_template: commandTemplate.trim(),
          description: 'Created by the authenticated operator.',
          trigger_type: triggerType,
          trigger_config: triggerConfig,
          next_run_at: nextRunAt,
          conditions: conditionField
            ? [{ field: conditionField, operator: 'eq', value: conditionValue }]
            : [],
        }),
      'Governed automation created.',
    );
    setName('');
    setCommandTemplate('');
  }

  if (loading || !user)
    return <main className="loading-page">Loading automations…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Governed autonomy</p>
          <h1>Automations</h1>
          <AutomationPolicyNote />
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {notice && <p className="workflow-success">{notice}</p>}
      <section className="workflow-panel">
        <h2>Build an automation</h2>
        <form className="workflow-form" onSubmit={handleCreate}>
          <label>
            Name
            <input
              required
              maxLength={255}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label>
            Trigger
            <select
              value={triggerType}
              onChange={(event) =>
                setTriggerType(event.target.value as Automation['trigger_type'])
              }
            >
              <option value="manual">Manual</option>
              <option value="schedule">Schedule</option>
              <option value="email_received">Email received</option>
              <option value="calendar_event">Calendar event</option>
              <option value="crm_change">CRM change</option>
              <option value="task_state">Task state</option>
              <option value="webhook">Webhook</option>
            </select>
          </label>
          {triggerType !== 'manual' && (
            <label>
              {triggerType === 'schedule'
                ? 'Interval in minutes'
                : triggerType === 'email_received'
                  ? 'Connected account UUID'
                  : triggerType === 'calendar_event'
                    ? 'Account UUID, calendar ID'
                    : triggerType === 'webhook'
                      ? 'Webhook source'
                      : 'Comma-separated values'}
              <input
                required
                value={triggerValue}
                onChange={(event) => setTriggerValue(event.target.value)}
              />
            </label>
          )}
          <label>
            Optional condition field
            <input
              value={conditionField}
              placeholder="payload.status"
              onChange={(event) => setConditionField(event.target.value)}
            />
          </label>
          {conditionField && (
            <label>
              Equals
              <input
                value={conditionValue}
                onChange={(event) => setConditionValue(event.target.value)}
              />
            </label>
          )}
          <label>
            Static command
            <textarea
              required
              maxLength={20000}
              value={commandTemplate}
              onChange={(event) => setCommandTemplate(event.target.value)}
            />
          </label>
          <p>
            Event payloads are stored as untrusted audit data and are never
            interpolated into this command.
          </p>
          <button disabled={busy} type="submit">
            Create automation
          </button>
        </form>
      </section>
      <section className="workflow-panel">
        <h2>Configured automations</h2>
        <div className="agent-grid">
          {automations.map((automation) => (
            <article className="agent-card" key={automation.id}>
              <p className="eyebrow">
                {automation.trigger_type} ·{' '}
                {automation.enabled ? 'active' : 'paused'}
              </p>
              <h3>{automation.name}</h3>
              <p>{automation.command_template}</p>
              <p>
                Depth {automation.max_depth} · {automation.max_runs_per_window}{' '}
                runs / {automation.window_seconds}s
              </p>
              <div className="button-row">
                <button
                  className="text-button"
                  disabled={busy}
                  type="button"
                  onClick={() => {
                    const updated = window.prompt(
                      'Static command for this automation',
                      automation.command_template,
                    );
                    if (!updated || updated === automation.command_template)
                      return;
                    void act(
                      () =>
                        updateAutomation(automation.id, {
                          command_template: updated,
                        }),
                      'Automation command updated.',
                    );
                  }}
                >
                  Edit command
                </button>
                <button
                  className="secondary-button"
                  disabled={busy}
                  type="button"
                  onClick={() =>
                    void act(
                      () =>
                        setAutomationEnabled(
                          automation.id,
                          !automation.enabled,
                        ),
                      automation.enabled
                        ? 'Automation paused.'
                        : 'Automation resumed.',
                    )
                  }
                >
                  {automation.enabled ? 'Pause' : 'Resume'}
                </button>
                {automation.trigger_type === 'manual' && automation.enabled && (
                  <button
                    disabled={busy}
                    type="button"
                    onClick={() =>
                      void act(
                        () =>
                          triggerManualAutomation(
                            automation.id,
                            `manual/${Date.now()}`,
                          ),
                        'A correlated command was created.',
                      )
                    }
                  >
                    Trigger
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
        {automations.length === 0 && (
          <p className="empty-state">No automations configured.</p>
        )}
      </section>
      <section className="workflow-panel">
        <h2>Recent runs</h2>
        <div className="activity-list">
          {runs.map((run) => (
            <article className="activity-item" key={run.id}>
              <AutomationRunSummary run={run} />
              {run.status === 'failed' && (
                <button
                  className="secondary-button"
                  disabled={busy}
                  type="button"
                  onClick={() =>
                    void act(
                      () => recoverAutomationRun(run.id),
                      'Recovery created one bounded retry run.',
                    )
                  }
                >
                  Recover
                </button>
              )}
            </article>
          ))}
        </div>
        {runs.length === 0 && <p className="empty-state">No runs yet.</p>}
      </section>
    </main>
  );
}
