'use client';

import { AGENT_CATALOG, type AgentId, type AgentOverview } from '@agent/shared';
import Link from 'next/link';
import React, { type ReactNode, useEffect, useState } from 'react';

import { aiErrorHint } from '../../lib/ai-errors';
import { KIKO_STATE_COPY, type KikoState } from '../../lib/kiko-state';
import {
  relativeTime,
  type ActiveExecution,
  type ActivityItem,
} from '../../lib/use-kiko-activity';
import { getAgentOverview } from '../../lib/workflow-client';
import { KikoIcon, type KikoIconName } from './kiko-icons';
import { operationalMessage } from '../../lib/labels';

/** Kiko's state as text (and a coloured dot). Screen readers hear changes politely. */
export function KikoStatusIndicator({
  state,
  showDetail = false,
}: {
  state: KikoState;
  showDetail?: boolean;
}) {
  const copy = KIKO_STATE_COPY[state];
  return (
    <p
      className={`kiko-status kiko-status--${state}`}
      role="status"
      aria-live="polite"
    >
      <span className="kiko-status__dot" aria-hidden="true" />
      <span className="kiko-status__label">{copy.label}</span>
      {showDetail ? (
        <span className="kiko-status__detail">{copy.detail}</span>
      ) : null}
    </p>
  );
}

/** Real progress of a plan (completed tasks over total tasks). */
export function KikoProgressRing({
  value,
  size = 64,
}: {
  value: number;
  size?: number;
}) {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));
  const radius = 26;
  const circumference = 2 * Math.PI * radius;
  return (
    <svg
      className="kiko-ring"
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label={`${clamped}% concluído`}
    >
      <circle className="kiko-ring__track" cx="32" cy="32" r={radius} />
      <circle
        className="kiko-ring__value"
        cx="32"
        cy="32"
        r={radius}
        strokeDasharray={circumference}
        strokeDashoffset={circumference * (1 - clamped / 100)}
      />
      <text x="32" y="36.5" textAnchor="middle" className="kiko-ring__text">
        {clamped}%
      </text>
    </svg>
  );
}

export function KikoExecutionCard({
  execution,
}: {
  execution: ActiveExecution;
}) {
  const progress = execution.progress;
  const total = progress?.total_tasks ?? 0;
  const done = progress?.completed_tasks ?? 0;
  return (
    <Link
      className="kiko-execution"
      href={`/dashboard/commands/${execution.command.id}`}
    >
      {progress ? (
        <KikoProgressRing value={progress.progress_percentage} />
      ) : (
        <span className="kiko-execution__pending" aria-hidden="true">
          <KikoIcon name="executions" size={22} />
        </span>
      )}
      <span className="kiko-execution__text">
        <strong>{execution.command.input}</strong>
        <span>
          {progress
            ? `${done} de ${total} ${total === 1 ? 'tarefa concluída' : 'tarefas concluídas'}`
            : 'Plano em preparação'}
          {progress && progress.waiting_approval_tasks > 0
            ? ` · ${progress.waiting_approval_tasks} à espera de aprovação`
            : ''}
          {progress && progress.failed_tasks > 0
            ? ` · ${progress.failed_tasks} com erro`
            : ''}
        </span>
      </span>
      <KikoIcon name="chevron" size={18} className="kiko-execution__chevron" />
    </Link>
  );
}

const AGENT_ICONS: Record<AgentId, KikoIconName> = {
  supervisor: 'plan',
  marketing: 'marketing',
  sales: 'crm',
  support: 'chat',
  development: 'code',
};

const AGENT_NAMES: Record<AgentId, string> = {
  supervisor: 'Supervisor',
  marketing: 'Marketing',
  sales: 'Vendas',
  support: 'Suporte',
  development: 'Desenvolvimento',
};

export function agentActivity(overview: AgentOverview | null): {
  text: string;
  tone: 'active' | 'waiting' | 'ready' | 'off' | 'unknown';
} {
  if (!overview) return { text: 'A verificar…', tone: 'unknown' };
  if (overview.operational_status === 'disabled')
    return { text: 'Desativado neste workspace', tone: 'off' };
  if (overview.operational_status === 'unavailable')
    return {
      text: operationalMessage(overview.operational_message),
      tone: 'off',
    };
  if (overview.tasks_running > 0)
    return {
      text: `A trabalhar em ${overview.tasks_running} ${overview.tasks_running === 1 ? 'tarefa' : 'tarefas'}`,
      tone: 'active',
    };
  if (overview.tasks_waiting_approval > 0)
    return {
      text: `${overview.tasks_waiting_approval} à espera de aprovação`,
      tone: 'waiting',
    };
  if (overview.tasks_pending > 0)
    return {
      text: `${overview.tasks_pending} ${overview.tasks_pending === 1 ? 'tarefa pendente' : 'tarefas pendentes'}`,
      tone: 'ready',
    };
  return { text: 'Pronto', tone: 'ready' };
}

/** The specialist agents and what each is doing now (from the API). */
export function KikoAgentList({ limit = 4 }: { limit?: number }) {
  const agents = AGENT_CATALOG.filter(
    (agent) => agent.id !== 'supervisor',
  ).slice(0, limit);
  const [overviews, setOverviews] = useState<
    Partial<Record<AgentId, AgentOverview | null>>
  >({});
  useEffect(() => {
    let active = true;
    for (const agent of agents) {
      void getAgentOverview(agent.id)
        .then((value) => {
          if (active)
            setOverviews((current) => ({ ...current, [agent.id]: value }));
        })
        .catch(() => {
          if (active)
            setOverviews((current) => ({ ...current, [agent.id]: null }));
        });
    }
    return () => {
      active = false;
    };
    // The catalogue is static.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <ul className="kiko-agents">
      {agents.map((agent) => {
        const overview = overviews[agent.id] ?? null;
        const activity = agentActivity(overview);
        return (
          <li key={agent.id}>
            <Link className="kiko-agent" href={`/dashboard/agents/${agent.id}`}>
              <span
                className={`kiko-agent__icon kiko-agent__icon--${agent.id}`}
                aria-hidden="true"
              >
                <KikoIcon name={AGENT_ICONS[agent.id]} size={18} />
              </span>
              <span className="kiko-agent__text">
                <strong>{AGENT_NAMES[agent.id]}</strong>
                <span>{activity.text}</span>
              </span>
              <span
                className={`kiko-agent__dot kiko-agent__dot--${activity.tone}`}
                aria-hidden="true"
              />
              <KikoIcon
                name="chevron"
                size={16}
                className="kiko-agent__chevron"
              />
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

const TONE_ICON: Record<ActivityItem['tone'], KikoIconName> = {
  success: 'check',
  warning: 'approvals',
  danger: 'alert',
  info: 'spark',
};

export function KikoActivityFeed({
  items,
  now = Date.now(),
}: {
  items: ActivityItem[];
  now?: number;
}) {
  if (items.length === 0)
    return (
      <KikoEmptyState
        icon="spark"
        title="Ainda sem atividade"
        text="Quando houver planos, ações ou alertas, aparecem aqui."
      />
    );
  return (
    <ul className="kiko-feed">
      {items.map((item) => {
        const body = (
          <>
            <span
              className={`kiko-feed__icon kiko-feed__icon--${item.tone}`}
              aria-hidden="true"
            >
              <KikoIcon name={TONE_ICON[item.tone]} size={16} />
            </span>
            <span className="kiko-feed__title">{item.title}</span>
            <time className="kiko-feed__time" dateTime={item.at}>
              {relativeTime(item.at, now)}
            </time>
          </>
        );
        return (
          <li key={item.id}>
            {item.href ? (
              <Link className="kiko-feed__item" href={item.href}>
                {body}
              </Link>
            ) : (
              <span className="kiko-feed__item">{body}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function KikoApprovalPanel({ pending }: { pending: number }) {
  if (pending === 0) return null;
  return (
    <Link className="kiko-approval" href="/dashboard/approvals">
      <KikoIcon name="approvals" size={22} />
      <span>
        <strong>
          {pending} {pending === 1 ? 'ação espera' : 'ações esperam'} pela tua
          decisão
        </strong>
        <span>Abrir o centro de aprovações</span>
      </span>
      <KikoIcon name="chevron" size={18} />
    </Link>
  );
}

export function KikoEmptyState({
  icon = 'spark',
  title,
  text,
  action,
}: {
  icon?: KikoIconName;
  title: string;
  text?: string;
  action?: ReactNode;
}) {
  return (
    <div className="kiko-empty">
      <KikoIcon name={icon} size={22} />
      <strong>{title}</strong>
      {text ? <span>{text}</span> : null}
      {action}
    </div>
  );
}

export function KikoLoadingState({
  label = 'A carregar…',
}: {
  label?: string;
}) {
  return (
    <div className="kiko-loading" role="status" aria-live="polite">
      <span className="kiko-loading__bar" aria-hidden="true" />
      <span className="kiko-loading__bar" aria-hidden="true" />
      <span className="kiko-visually-hidden">{label}</span>
    </div>
  );
}

export function KikoErrorState({ message }: { message: string }) {
  const hint = aiErrorHint(message);
  return (
    <div className="kiko-error" role="alert">
      <KikoIcon name="alert" size={20} />
      <span>
        <strong>{message}</strong>
        {hint ? <span>{hint}</span> : null}
      </span>
    </div>
  );
}

export function KikoSection({
  title,
  action,
  children,
  id,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  id?: string;
}) {
  const headingId = id ? `${id}-title` : undefined;
  return (
    <section className="kiko-card" aria-labelledby={headingId}>
      <header className="kiko-card__header">
        <h2 id={headingId}>{title}</h2>
        {action}
      </header>
      {children}
    </section>
  );
}
