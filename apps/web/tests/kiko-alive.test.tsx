import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { KikoAvatar } from '../components/kiko/kiko-avatar';
import {
  agentActivity,
  KikoProgressRing,
  KikoStatusIndicator,
} from '../components/kiko/kiko-ui';
import {
  COMMAND_STEPS,
  commandStage,
  KikoWorkspaceMode,
} from '../components/kiko/kiko-workspace';
import {
  deriveKikoState,
  firstName,
  greeting,
  KIKO_STATES,
  KIKO_STATE_COPY,
  SLEEP_AFTER_MS,
  type KikoSignals,
} from '../lib/kiko-state';
import { buildActivity, relativeTime } from '../lib/use-kiko-activity';

vi.mock('../lib/auth-client', () => ({
  authFetch: vi.fn(),
  apiFetch: vi.fn(),
  logout: vi.fn(),
}));

const calm: KikoSignals = {
  apiOnline: true,
  aiAvailable: true,
  pendingApprovals: 0,
  activeAgentRuns: 0,
  planningCommands: 0,
};

describe('Kiko state machine (real signals only)', () => {
  it('is idle when nothing is happening', () => {
    expect(deriveKikoState(calm)).toBe('idle');
  });

  it('follows the workspace: executing beats approvals beats planning', () => {
    expect(deriveKikoState({ ...calm, planningCommands: 1 })).toBe('planning');
    expect(
      deriveKikoState({ ...calm, planningCommands: 1, pendingApprovals: 2 }),
    ).toBe('waiting_approval');
    expect(
      deriveKikoState({ ...calm, pendingApprovals: 2, activeAgentRuns: 1 }),
    ).toBe('executing');
  });

  it('puts what the person is doing first, and offline above everything', () => {
    const busy = { ...calm, activeAgentRuns: 3 };
    expect(deriveKikoState({ ...busy, listening: true })).toBe('listening');
    expect(deriveKikoState({ ...busy, thinking: true })).toBe('thinking');
    expect(deriveKikoState({ ...busy, outcome: 'success' })).toBe('success');
    expect(deriveKikoState({ ...busy, outcome: 'error' })).toBe('error');
    expect(deriveKikoState({ ...busy, thinking: true, apiOnline: false })).toBe(
      'offline',
    );
  });

  it('shows an error when the local AI is unavailable, and sleeps when idle', () => {
    expect(deriveKikoState({ ...calm, aiAvailable: false })).toBe('error');
    expect(deriveKikoState({ ...calm, idleForMs: SLEEP_AFTER_MS })).toBe(
      'sleeping',
    );
    expect(
      deriveKikoState({
        ...calm,
        idleForMs: SLEEP_AFTER_MS,
        activeAgentRuns: 1,
      }),
    ).toBe('executing');
  });

  it('has text for every state', () => {
    for (const state of KIKO_STATES) {
      expect(KIKO_STATE_COPY[state].label.length).toBeGreaterThan(0);
    }
  });

  it('greets by time of day and first name', () => {
    expect(greeting(new Date(2026, 10, 20, 9))).toBe('Bom dia');
    expect(greeting(new Date(2026, 10, 20, 15))).toBe('Boa tarde');
    expect(greeting(new Date(2026, 10, 20, 22))).toBe('Boa noite');
    expect(firstName('Tiago Santos')).toBe('Tiago');
    expect(firstName(null)).toBe('');
  });
});

describe('Kiko avatar', () => {
  it('renders every state with an accessible label', () => {
    for (const state of KIKO_STATES) {
      const markup = renderToStaticMarkup(<KikoAvatar state={state} />);
      expect(markup).toContain(`data-state="${state}"`);
      expect(markup).toContain(
        `aria-label="Kiko — ${KIKO_STATE_COPY[state].label}"`,
      );
    }
  });

  it('is hidden from assistive technology when decorative', () => {
    const markup = renderToStaticMarkup(<KikoAvatar state="idle" decorative />);
    expect(markup).toContain('aria-hidden="true"');
    expect(markup).not.toContain('role="img"');
  });

  it('never relies on the drawing alone: the status is text in a live region', () => {
    const markup = renderToStaticMarkup(
      <KikoStatusIndicator state="waiting_approval" showDetail />,
    );
    expect(markup).toContain('role="status"');
    expect(markup).toContain('À espera de aprovação');
  });
});

describe('progress and activity', () => {
  it('shows the real percentage, clamped', () => {
    expect(renderToStaticMarkup(<KikoProgressRing value={72.4} />)).toContain(
      '72%',
    );
    expect(renderToStaticMarkup(<KikoProgressRing value={140} />)).toContain(
      '100%',
    );
  });

  it('merges notifications and executions newest first', () => {
    const feed = buildActivity(
      [
        {
          id: 'n1',
          title: 'Plano aprovado',
          created_at: '2026-11-20T10:00:00Z',
          href: null,
          kind: 'plan_approved',
        },
      ],
      [
        {
          id: 'e1',
          task_id: 't1',
          tool_name: 'internal.echo',
          status: 'failed',
          duration_ms: 10,
          created_at: '2026-11-20T11:00:00Z',
        },
      ],
    );
    expect(feed.map((item) => item.id)).toEqual(['e-e1', 'n-n1']);
    expect(feed[0]).toMatchObject({
      tone: 'danger',
      href: '/dashboard/tasks/t1',
    });
  });

  it('describes elapsed time in Portuguese', () => {
    const now = Date.parse('2026-11-20T12:00:00Z');
    expect(relativeTime('2026-11-20T11:59:40Z', now)).toBe('Agora');
    expect(relativeTime('2026-11-20T11:48:00Z', now)).toBe('Há 12 min');
    expect(relativeTime('2026-11-20T09:00:00Z', now)).toBe('Há 3 h');
    expect(relativeTime('2026-11-18T12:00:00Z', now)).toBe('Há 2 dias');
  });

  it('describes what each agent is doing from its overview', () => {
    const base = {
      operational_status: 'operational',
      operational_message: 'ok',
      tasks_pending: 0,
      tasks_running: 0,
      tasks_waiting_approval: 0,
      tasks_failed: 0,
    };
    expect(agentActivity(null).tone).toBe('unknown');
    expect(agentActivity({ ...base, tasks_running: 2 } as never)).toEqual({
      text: 'A trabalhar em 2 tarefas',
      tone: 'active',
    });
    expect(
      agentActivity({ ...base, tasks_waiting_approval: 1 } as never).tone,
    ).toBe('waiting');
    expect(
      agentActivity({
        ...base,
        operational_status: 'unavailable',
        operational_message: 'Local AI runtime is not reachable',
      } as never),
    ).toEqual({ text: 'Local AI runtime is not reachable', tone: 'off' });
    expect(agentActivity(base as never)).toEqual({
      text: 'Pronto',
      tone: 'ready',
    });
  });
});

describe('adaptive command workspace', () => {
  const task = (status: string) => ({ status }) as never;

  it('moves through planning, approval, execution and result', () => {
    expect(commandStage({ status: 'pending' }, null, [], false)).toMatchObject({
      mode: 'planning',
      step: 1,
      state: 'idle',
    });
    expect(commandStage({ status: 'planning' }, null, [], true).state).toBe(
      'planning',
    );
    expect(
      commandStage({ status: 'planning' }, { status: 'draft' }, [], false),
    ).toMatchObject({ step: 2, state: 'waiting_approval' });
    expect(
      commandStage(
        { status: 'in_progress' },
        { status: 'approved' } as never,
        [task('running'), task('completed')],
        false,
      ),
    ).toMatchObject({
      mode: 'execution',
      step: 3,
      state: 'executing',
      detail: '1 de 2 tarefas concluídas · 1 a decorrer.',
    });
    expect(commandStage({ status: 'completed' }, null, [], false).state).toBe(
      'success',
    );
    expect(commandStage({ status: 'failed' }, null, [], false).state).toBe(
      'error',
    );
  });

  it('marks finished steps and the current step', () => {
    const markup = renderToStaticMarkup(
      <KikoWorkspaceMode
        mode="planning"
        state="waiting_approval"
        detail="Pronto"
        step={2}
        steps={COMMAND_STEPS}
      />,
    );
    expect(markup).toContain('Modo de planeamento');
    expect(markup.match(/class="is-done"/g)).toHaveLength(2);
    expect(markup).toContain('aria-current="step">Aprovação');
  });
});
