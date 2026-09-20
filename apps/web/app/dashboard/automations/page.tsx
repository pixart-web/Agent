'use client';

import type { Automation, AutomationRun } from '@agent/shared';
import { FormEvent, useCallback, useEffect, useState } from 'react';

import {
  AutomationPolicyNote,
  AutomationRunSummary,
} from '../../../components/automation-summary';
import { DashboardNav } from '../../../components/dashboard-nav';
import {
  createManualAutomation,
  listAutomationRuns,
  listAutomations,
  recoverAutomationRun,
  setAutomationEnabled,
  triggerManualAutomation,
} from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function AutomationsPage() {
  const { user, loading } = useAuthenticatedUser();
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [name, setName] = useState('');
  const [commandTemplate, setCommandTemplate] = useState('');
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
    await act(
      () =>
        createManualAutomation({
          name: name.trim(),
          command_template: commandTemplate.trim(),
          description: 'Created by the authenticated operator.',
        }),
      'Manual automation created.',
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
        <h2>Create a manual automation</h2>
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
