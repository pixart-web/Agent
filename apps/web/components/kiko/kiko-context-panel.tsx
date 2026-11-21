'use client';

import Link from 'next/link';
import React, { useEffect, useRef } from 'react';

import { buildActivity, useKikoActivity } from '../../lib/use-kiko-activity';
import type { KikoLiveData } from '../../lib/use-kiko-signals';
import { KikoIcon } from './kiko-icons';
import {
  KikoActivityFeed,
  KikoAgentList,
  KikoApprovalPanel,
  KikoEmptyState,
  KikoErrorState,
  KikoExecutionCard,
  KikoLoadingState,
  KikoSection,
} from './kiko-ui';

/**
 * What is happening in the workspace now: executions in progress, approvals waiting,
 * agents and recent activity. Docked on the home screen; a closable drawer elsewhere.
 * Sections without real content are left out.
 */
export function KikoContextPanel({
  id,
  live,
  variant,
  onClose,
}: {
  id?: string;
  live: KikoLiveData;
  variant: 'docked' | 'drawer';
  onClose?: () => void;
}) {
  const activity = useKikoActivity(live.refreshedAt);
  const panel = useRef<HTMLElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const feed = buildActivity(
    activity.notifications,
    live.overview?.recent_executions ?? [],
  );

  useEffect(() => {
    if (variant !== 'drawer') return;
    panel.current?.focus();
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') closeRef.current?.();
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [variant]);

  return (
    <aside
      id={id}
      ref={panel}
      tabIndex={-1}
      className={`kiko-context kiko-context--${variant}`}
      aria-label="Atividade do workspace"
    >
      {variant === 'drawer' ? (
        <div className="kiko-context__bar">
          <strong>Atividade</strong>
          <button
            type="button"
            className="kiko-icon-button"
            onClick={onClose}
            aria-label="Fechar painel de atividade"
          >
            <KikoIcon name="collapse" />
          </button>
        </div>
      ) : null}

      {live.apiOnline === false ? (
        <KikoErrorState message="Sem ligação ao servidor Kiko." />
      ) : null}

      <KikoApprovalPanel pending={live.overview?.pending_approvals ?? 0} />

      <KikoSection
        id={`${variant}-executions`}
        title="Execução em curso"
        action={
          <Link className="kiko-card__link" href="/dashboard/commands">
            Comandos
          </Link>
        }
      >
        {!activity.loaded ? (
          <KikoLoadingState label="A carregar execuções" />
        ) : activity.executions.length === 0 ? (
          <KikoEmptyState
            icon="executions"
            title="Nada em execução"
            text="Os planos aprovados aparecem aqui com o progresso real."
          />
        ) : (
          activity.executions.map((execution) => (
            <KikoExecutionCard
              key={execution.command.id}
              execution={execution}
            />
          ))
        )}
      </KikoSection>

      <KikoSection
        id={`${variant}-agents`}
        title="Agentes"
        action={
          <Link className="kiko-card__link" href="/dashboard/agents">
            Ver todos
          </Link>
        }
      >
        <KikoAgentList />
      </KikoSection>

      <KikoSection
        id={`${variant}-activity`}
        title="Atividade recente"
        action={
          <Link className="kiko-card__link" href="/dashboard/notifications">
            Ver tudo
          </Link>
        }
      >
        {activity.loaded ? (
          <KikoActivityFeed items={feed} />
        ) : (
          <KikoLoadingState label="A carregar atividade" />
        )}
      </KikoSection>
    </aside>
  );
}
