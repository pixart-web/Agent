'use client';

import type { Command, PlanProgress } from '@agent/shared';
import { useEffect, useState } from 'react';

import { listNotifications } from './notification-client';
import type { RecentExecution } from './operations-client';
import { getPlan, getPlanProgress, listCommands } from './workflow-client';

export type ActiveExecution = {
  command: Command;
  planId: string | null;
  progress: PlanProgress | null;
};

export type ActivityItem = {
  id: string;
  kind: 'notification' | 'execution';
  title: string;
  at: string;
  href: string | null;
  tone: 'success' | 'warning' | 'danger' | 'info';
};

const EXECUTION_TONE: Record<string, ActivityItem['tone']> = {
  succeeded: 'success',
  completed: 'success',
  failed: 'danger',
  delivery_unknown: 'warning',
  cancelled: 'warning',
};

const TOOL_LABELS: Record<string, string> = {
  'internal.echo': 'Nota interna',
  'internal.create_note': 'Nota interna criada',
};

export function executionTitle(execution: RecentExecution): string {
  const tool = TOOL_LABELS[execution.tool_name] ?? execution.tool_name;
  const status =
    execution.status === 'succeeded'
      ? 'concluída'
      : execution.status === 'failed'
        ? 'falhou'
        : execution.status.replace(/_/g, ' ');
  return `Ação ${tool} ${status}`;
}

/** Merge notifications and executions into one feed, newest first. */
export function buildActivity(
  notifications: {
    id: string;
    title: string;
    created_at: string;
    href: string | null;
    kind: string;
  }[],
  executions: RecentExecution[],
  limit = 6,
): ActivityItem[] {
  const items: ActivityItem[] = [
    ...notifications.map((item) => ({
      id: `n-${item.id}`,
      kind: 'notification' as const,
      title: item.title,
      at: item.created_at,
      href: item.href,
      tone: /fail|error|falh/i.test(item.kind)
        ? ('danger' as const)
        : /approval/i.test(item.kind)
          ? ('warning' as const)
          : ('info' as const),
    })),
    ...executions.map((item) => ({
      id: `e-${item.id}`,
      kind: 'execution' as const,
      title: executionTitle(item),
      at: item.created_at,
      href: `/dashboard/tasks/${item.task_id}`,
      tone: EXECUTION_TONE[item.status] ?? ('info' as const),
    })),
  ];
  return items
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at))
    .slice(0, limit);
}

/** "Agora", "Há 12 min", "Há 3 h", "Há 2 dias" for a past ISO timestamp. */
export function relativeTime(iso: string, now = Date.now()): string {
  const minutes = Math.round((now - Date.parse(iso)) / 60_000);
  if (minutes < 1) return 'Agora';
  if (minutes < 60) return `Há ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `Há ${hours} h`;
  const days = Math.round(hours / 24);
  return days === 1 ? 'Há 1 dia' : `Há ${days} dias`;
}

async function loadExecutions(limit: number): Promise<ActiveExecution[]> {
  const commands = await listCommands({ status: 'in_progress', limit });
  return Promise.all(
    commands.map(async (command) => {
      try {
        const plan = await getPlan(command.id);
        const progress = await getPlanProgress(plan.id);
        return { command, planId: plan.id, progress };
      } catch {
        return { command, planId: null, progress: null };
      }
    }),
  );
}

export type KikoActivity = {
  loaded: boolean;
  executions: ActiveExecution[];
  notifications: Awaited<ReturnType<typeof listNotifications>>['notifications'];
  failed: boolean;
};

/** Commands in progress (with real plan progress) and recent notifications. */
export function useKikoActivity(
  refreshKey = 0,
  executionLimit = 3,
): KikoActivity {
  const [state, setState] = useState<KikoActivity>({
    loaded: false,
    executions: [],
    notifications: [],
    failed: false,
  });
  useEffect(() => {
    let active = true;
    async function load() {
      const [executions, notifications] = await Promise.all([
        loadExecutions(executionLimit).catch(() => null),
        listNotifications()
          .then((value) => value.notifications)
          .catch(() => null),
      ]);
      if (!active) return;
      setState({
        loaded: true,
        executions: executions ?? [],
        notifications: notifications ?? [],
        failed: executions === null && notifications === null,
      });
    }
    void load();
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void load();
    }, 30_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [refreshKey, executionLimit]);
  return state;
}
