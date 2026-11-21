import type { Command, Plan, TaskDetail } from '@agent/shared';
import React from 'react';

import { KIKO_STATE_COPY, type KikoState } from '../../lib/kiko-state';
import { KikoAvatar } from './kiko-avatar';

export type WorkspaceMode =
  'planning' | 'execution' | 'analysis' | 'conversation';

const MODE_LABEL: Record<WorkspaceMode, string> = {
  planning: 'Modo de planeamento',
  execution: 'Modo de execução',
  analysis: 'Modo de análise',
  conversation: 'Modo de conversa',
};

export const COMMAND_STEPS = [
  'Pedido',
  'Plano',
  'Aprovação',
  'Execução',
  'Resultado',
] as const;

export type CommandStage = {
  mode: WorkspaceMode;
  step: number;
  state: KikoState;
  detail: string;
};

/** Where a command stands, from its real status, plan and tasks. */
export function commandStage(
  command: Pick<Command, 'status'>,
  plan: Pick<Plan, 'status'> | null,
  tasks: Pick<TaskDetail, 'status'>[],
  planningRunActive: boolean,
): CommandStage {
  const running = tasks.filter((task) => task.status === 'running').length;
  const waiting = tasks.filter(
    (task) => task.status === 'waiting_approval',
  ).length;
  const done = tasks.filter((task) => task.status === 'completed').length;
  switch (command.status) {
    case 'completed':
      return {
        mode: 'execution',
        step: 4,
        state: 'success',
        detail: 'O comando foi concluído.',
      };
    case 'failed':
      return {
        mode: 'execution',
        step: 3,
        state: 'error',
        detail: 'O comando falhou. Revê as tarefas com erro.',
      };
    case 'cancelled':
      return {
        mode: 'execution',
        step: 3,
        state: 'sleeping',
        detail: 'O comando foi cancelado.',
      };
    case 'in_progress':
      return {
        mode: 'execution',
        step: 3,
        state:
          running > 0 ? 'executing' : waiting > 0 ? 'waiting_approval' : 'idle',
        detail: `${done} de ${tasks.length} tarefas concluídas${running ? ` · ${running} a decorrer` : ''}${waiting ? ` · ${waiting} à espera de aprovação` : ''}.`,
      };
    default:
      if (planningRunActive)
        return {
          mode: 'planning',
          step: 1,
          state: 'planning',
          detail: 'O Supervisor está a preparar o plano com a IA local.',
        };
      if (plan?.status === 'draft')
        return {
          mode: 'planning',
          step: 2,
          state: 'waiting_approval',
          detail: 'O plano está pronto. Revê e aprova para começar.',
        };
      return {
        mode: 'planning',
        step: 1,
        state: 'idle',
        detail: 'Gera um plano com o Supervisor ou cria-o manualmente.',
      };
  }
}

/** Header of an adaptive workspace: mode, Kiko's state and (optionally) the steps. */
export function KikoWorkspaceMode({
  mode,
  state,
  detail,
  step,
  steps,
}: {
  mode: WorkspaceMode;
  state: KikoState;
  detail: string;
  step?: number;
  steps?: readonly string[];
}) {
  return (
    <section className="kiko-workspace-mode" aria-label={MODE_LABEL[mode]}>
      <KikoAvatar state={state} size={64} decorative />
      <div className="kiko-workspace-mode__text">
        <p className="kiko-workspace-mode__eyebrow">{MODE_LABEL[mode]}</p>
        <strong>{KIKO_STATE_COPY[state].label}</strong>
        <p role="status">{detail}</p>
        {steps && step !== undefined ? (
          <ol className="kiko-steps" aria-label="Etapas">
            {steps.map((label, index) => (
              <li
                key={label}
                className={index < step ? 'is-done' : undefined}
                aria-current={index === step ? 'step' : undefined}
              >
                {label}
              </li>
            ))}
          </ol>
        ) : null}
      </div>
    </section>
  );
}
