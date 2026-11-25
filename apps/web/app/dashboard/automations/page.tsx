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
import { CanEdit } from '../../../lib/workspace-access';
import { label } from '../../../lib/labels';
import { failureMessage } from '../../../lib/api-messages';

function formatWindow(seconds: number): string {
  if (seconds % 86400 === 0) {
    const days = seconds / 86400;
    return days === 1 ? '1 dia' : `${days} dias`;
  }
  if (seconds % 3600 === 0) return `${seconds / 3600} h`;
  if (seconds % 60 === 0) return `${seconds / 60} min`;
  return `${seconds} s`;
}

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
      void refresh().catch(() =>
        setError('Não foi possível carregar as automatizações.'),
      );
  }, [refresh, user]);

  async function act(operation: () => Promise<unknown>, message: string) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await operation();
      await refresh();
      setNotice(message);
    } catch (failure) {
      setError(
        failureMessage(
          failure,
          'Não foi possível concluir a operação da automatização.',
        ),
      );
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
          description: 'Criado pelo operador autenticado.',
          trigger_type: triggerType,
          trigger_config: triggerConfig,
          next_run_at: nextRunAt,
          conditions: conditionField
            ? [{ field: conditionField, operator: 'eq', value: conditionValue }]
            : [],
        }),
      'Automatização governada criada.',
    );
    setName('');
    setCommandTemplate('');
  }

  if (loading || !user)
    return <main className="loading-page">A carregar as automatizações…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Autonomia governada</p>
          <h1>Automatizações</h1>
          <AutomationPolicyNote />
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {notice && <p className="workflow-success">{notice}</p>}
      <CanEdit>
        <section className="workflow-panel">
          <h2>Criar uma automatização</h2>
          <form className="workflow-form" onSubmit={handleCreate}>
            <label>
              Nome
              <input
                required
                maxLength={255}
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label>
              Gatilho
              <select
                value={triggerType}
                onChange={(event) =>
                  setTriggerType(
                    event.target.value as Automation['trigger_type'],
                  )
                }
              >
                <option value="manual">Manual</option>
                <option value="schedule">Agendamento</option>
                <option value="email_received">Email recebido</option>
                <option value="calendar_event">Evento de calendário</option>
                <option value="crm_change">Alteração no CRM</option>
                <option value="task_state">Estado da tarefa</option>
                <option value="webhook">Webhook</option>
              </select>
            </label>
            {triggerType !== 'manual' && (
              <label>
                {triggerType === 'schedule'
                  ? 'Intervalo em minutos'
                  : triggerType === 'email_received'
                    ? 'UUID da conta ligada'
                    : triggerType === 'calendar_event'
                      ? 'UUID da conta, ID do calendário'
                      : triggerType === 'webhook'
                        ? 'Origem do webhook'
                        : 'Valores separados por vírgulas'}
                <input
                  required
                  value={triggerValue}
                  onChange={(event) => setTriggerValue(event.target.value)}
                />
              </label>
            )}
            <label>
              Campo de condição (opcional)
              <input
                value={conditionField}
                placeholder="payload.status"
                onChange={(event) => setConditionField(event.target.value)}
              />
            </label>
            {conditionField && (
              <label>
                Igual a
                <input
                  value={conditionValue}
                  onChange={(event) => setConditionValue(event.target.value)}
                />
              </label>
            )}
            <label>
              Comando fixo
              <textarea
                required
                maxLength={20000}
                value={commandTemplate}
                onChange={(event) => setCommandTemplate(event.target.value)}
              />
            </label>
            <p>
              Os dados dos eventos ficam guardados na auditoria como não
              verificados e nunca entram neste comando.
            </p>
            <button disabled={busy} type="submit">
              Criar automatização
            </button>
          </form>
        </section>
      </CanEdit>
      <section className="workflow-panel">
        <h2>Automatizações configuradas</h2>
        <div className="agent-grid">
          {automations.map((automation) => (
            <article className="agent-card" key={automation.id}>
              <p className="eyebrow">
                {label(automation.trigger_type)} ·{' '}
                {automation.enabled ? 'Ativa' : 'Em pausa'}
              </p>
              <h3>{automation.name}</h3>
              <p>{automation.command_template}</p>
              <p>
                Profundidade máx. {automation.max_depth} · até{' '}
                {automation.max_runs_per_window} execuções em{' '}
                {formatWindow(automation.window_seconds)}
              </p>
              <CanEdit>
                <div className="button-row">
                  <button
                    className="text-button"
                    disabled={busy}
                    type="button"
                    onClick={() => {
                      const updated = window.prompt(
                        'Comando fixo desta automatização',
                        automation.command_template,
                      );
                      if (!updated || updated === automation.command_template)
                        return;
                      void act(
                        () =>
                          updateAutomation(automation.id, {
                            command_template: updated,
                          }),
                        'Comando da automatização atualizado.',
                      );
                    }}
                  >
                    Editar comando
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
                          ? 'Automatização em pausa.'
                          : 'Automatização retomada.',
                      )
                    }
                  >
                    {automation.enabled ? 'Pausar' : 'Retomar'}
                  </button>
                  {automation.trigger_type === 'manual' &&
                    automation.enabled && (
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
                            'Foi criado um comando correlacionado.',
                          )
                        }
                      >
                        Gatilho
                      </button>
                    )}
                </div>
              </CanEdit>
            </article>
          ))}
        </div>
        {automations.length === 0 && (
          <p className="empty-state">Nenhuma automatização configurada.</p>
        )}
      </section>
      <section className="workflow-panel">
        <h2>Execuções recentes</h2>
        <div className="activity-list">
          {runs.map((run) => (
            <article className="activity-item" key={run.id}>
              <AutomationRunSummary run={run} />
              <CanEdit>
                {run.status === 'failed' && (
                  <button
                    className="secondary-button"
                    disabled={busy}
                    type="button"
                    onClick={() =>
                      void act(
                        () => recoverAutomationRun(run.id),
                        'A recuperação criou uma nova tentativa limitada.',
                      )
                    }
                  >
                    Recuperar
                  </button>
                )}
              </CanEdit>
            </article>
          ))}
        </div>
        {runs.length === 0 && (
          <p className="empty-state">Ainda sem execuções.</p>
        )}
      </section>
    </main>
  );
}
