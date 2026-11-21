'use client';

import type { Conversation } from '@agent/shared';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import React, { type FormEvent, useEffect, useRef, useState } from 'react';

import type { User } from '../../lib/auth-types';
import { deriveKikoState, firstName, greeting } from '../../lib/kiko-state';
import {
  signalsFrom,
  useIdleTime,
  useKikoLiveData,
} from '../../lib/use-kiko-signals';
import {
  createConversation,
  getCalendarIntegrationStatus,
  getCodexIntegrationStatus,
  getEmailIntegrationStatus,
  getGitHubIntegrationStatus,
  listConversations,
  WorkflowApiError,
} from '../../lib/workflow-client';
import { canEdit, useWorkspaceAccess } from '../../lib/workspace-access';
import { KikoAvatar } from './kiko-avatar';
import { KikoContextPanel } from './kiko-context-panel';
import { KikoIcon, type KikoIconName } from './kiko-icons';
import { KikoErrorState, KikoStatusIndicator } from './kiko-ui';

export const QUICK_ACTIONS: {
  href: string;
  icon: KikoIconName;
  title: string;
  text: string;
}[] = [
  {
    href: '/dashboard/commands/new',
    icon: 'plan',
    title: 'Criar um plano',
    text: 'Descreve o objetivo e o Supervisor propõe as etapas.',
  },
  {
    href: '/dashboard/tasks',
    icon: 'layers',
    title: 'Executar uma tarefa',
    text: 'Põe os agentes a trabalhar nas tarefas prontas.',
  },
  {
    href: '/dashboard/analytics',
    icon: 'reports',
    title: 'Analisar resultados',
    text: 'Comandos, execuções e custos dos últimos dias.',
  },
  {
    href: '/dashboard/automations',
    icon: 'automations',
    title: 'Automatizar um processo',
    text: 'Cria um fluxo que corre sozinho, com aprovação.',
  },
];

function formatDate(date: Date): string {
  const text = new Intl.DateTimeFormat('pt-PT', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(date);
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** The natural-language request box: starts a Kiko conversation with the local AI. */
export function KikoCommandBar({
  disabled,
  onActivity,
}: {
  disabled: boolean;
  onActivity: (activity: {
    listening?: boolean;
    thinking?: boolean;
    outcome?: 'success' | 'error' | null;
  }) => void;
}) {
  const router = useRouter();
  const input = useRef<HTMLTextAreaElement>(null);
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [recent, setRecent] = useState<Conversation[]>([]);

  useEffect(() => {
    void listConversations()
      .then((items) => setRecent(items.slice(0, 3)))
      .catch(() => undefined);
  }, []);

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const content = message.trim();
    if (!content || submitting || disabled) return;
    setSubmitting(true);
    setError('');
    onActivity({ thinking: true, listening: false, outcome: null });
    try {
      const turn = await createConversation(content);
      onActivity({ thinking: false, outcome: 'success' });
      router.push(`/dashboard/kiko/${turn.conversation.id}`);
    } catch (submitError) {
      setError(
        submitError instanceof WorkflowApiError
          ? submitError.message
          : 'Não foi possível enviar o pedido. Tenta de novo.',
      );
      onActivity({ thinking: false, outcome: 'error' });
      setSubmitting(false);
    }
  }

  return (
    <div className="kiko-command">
      <form
        className={`kiko-command__box${submitting ? ' is-busy' : ''}`}
        onSubmit={submit}
        aria-busy={submitting}
      >
        <KikoIcon name="spark" size={22} className="kiko-command__spark" />
        <label className="kiko-visually-hidden" htmlFor="kiko-request">
          Pedido para o Kiko
        </label>
        <textarea
          id="kiko-request"
          ref={input}
          rows={1}
          maxLength={8000}
          value={message}
          disabled={disabled || submitting}
          placeholder={
            disabled
              ? 'Só de leitura: pede acesso de edição para fazer pedidos.'
              : 'O que queres que eu faça hoje?'
          }
          onChange={(event) => setMessage(event.target.value)}
          onFocus={() => onActivity({ listening: true, outcome: null })}
          onBlur={() => onActivity({ listening: false })}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
        />
        <button
          type="submit"
          className="kiko-command__send"
          disabled={disabled || submitting || !message.trim()}
          aria-label={submitting ? 'A enviar o pedido' : 'Enviar pedido'}
        >
          <KikoIcon name="send" size={20} />
        </button>
      </form>
      <p className="kiko-command__hint">
        {submitting
          ? 'A IA local está a preparar a resposta. Pode demorar até um minuto.'
          : 'Enter envia · Shift+Enter muda de linha · Tudo corre na IA local da Pixart.'}
      </p>
      {error ? <KikoErrorState message={error} /> : null}
      {recent.length > 0 ? (
        <nav className="kiko-command__recent" aria-label="Conversas recentes">
          <span>Continuar</span>
          {recent.map((item) => (
            <Link key={item.id} href={`/dashboard/kiko/${item.id}`}>
              {item.title}
            </Link>
          ))}
        </nav>
      ) : null}
    </div>
  );
}

type Ecosystem = {
  name: string;
  icon: KikoIconName;
  state: string;
  ok: boolean;
};

function integrationState(
  value: {
    enabled: boolean;
    operational_state?: string;
    credential_configured?: boolean;
  } | null,
): { state: string; ok: boolean } {
  if (!value) return { state: 'Indisponível', ok: false };
  if (!value.enabled) return { state: 'Desativado', ok: false };
  if (value.operational_state) {
    const ok = value.operational_state === 'connected';
    const labels: Record<string, string> = {
      connected: 'Ligado',
      not_connected: 'Por ligar',
      degraded: 'Com problemas',
      reconciliation_required: 'Requer revisão',
      disabled: 'Desativado',
    };
    return {
      state: labels[value.operational_state] ?? value.operational_state,
      ok,
    };
  }
  return value.credential_configured
    ? { state: 'Configurado', ok: true }
    : { state: 'Sem credenciais', ok: false };
}

/** Integrations as the server reports them; nothing is shown as active unless it is. */
export function KikoEcosystem() {
  const [items, setItems] = useState<Ecosystem[] | null>(null);
  useEffect(() => {
    let active = true;
    void Promise.all([
      getEmailIntegrationStatus().catch(() => null),
      getCalendarIntegrationStatus().catch(() => null),
      getGitHubIntegrationStatus().catch(() => null),
      getCodexIntegrationStatus().catch(() => null),
    ]).then(([email, calendar, github, codex]) => {
      if (!active) return;
      setItems([
        { name: 'Email', icon: 'email', ...integrationState(email) },
        { name: 'Calendário', icon: 'calendar', ...integrationState(calendar) },
        { name: 'GitHub', icon: 'code', ...integrationState(github) },
        { name: 'Codex', icon: 'layers', ...integrationState(codex) },
      ]);
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="kiko-ecosystem" aria-labelledby="kiko-ecosystem-title">
      <h2 id="kiko-ecosystem-title">
        <KikoIcon name="link" size={16} /> O teu ecossistema
      </h2>
      <ul>
        {(items ?? []).map((item) => (
          <li key={item.name} className={item.ok ? 'is-on' : undefined}>
            <KikoIcon name={item.icon} size={18} />
            <span>
              <strong>{item.name}</strong>
              <span>{item.state}</span>
            </span>
          </li>
        ))}
      </ul>
      <Link className="kiko-card__link" href="/dashboard/integrations">
        Gerir integrações
      </Link>
    </section>
  );
}

export function KikoHome({ user }: { user: User }) {
  const live = useKikoLiveData();
  const idle = useIdleTime();
  const access = useWorkspaceAccess();
  const [local, setLocal] = useState<{
    listening?: boolean;
    thinking?: boolean;
    outcome?: 'success' | 'error' | null;
  }>({});
  const [now] = useState(() => new Date());

  // A success or error expression is shown briefly, then Kiko goes back to the live state.
  useEffect(() => {
    if (!local.outcome) return;
    const timer = window.setTimeout(
      () => setLocal((current) => ({ ...current, outcome: null })),
      4000,
    );
    return () => window.clearTimeout(timer);
  }, [local.outcome]);

  const state = deriveKikoState({
    ...signalsFrom(live),
    ...local,
    idleForMs: idle,
  });
  const name = firstName(user.full_name);
  const readOnly = access.loaded && !canEdit(access.role);

  return (
    <div className="kiko-home">
      <div className="kiko-home__main">
        <header className="kiko-home__greeting">
          <h1>
            {greeting(now)}
            {name ? `, ${name}` : ''}
          </h1>
          <p>{formatDate(now)}</p>
        </header>

        <section className="kiko-hero" aria-labelledby="kiko-hero-title">
          <div className="kiko-hero__backdrop" aria-hidden="true" />
          <div className="kiko-hero__copy">
            <h2 id="kiko-hero-title">
              Olá, eu sou o <span>Kiko.</span>
            </h2>
            <p>
              O teu agente de IA para planear, executar e acompanhar o trabalho
              em todo o ecossistema Pixart.
            </p>
            <KikoStatusIndicator state={state} showDetail />
          </div>
          <div className="kiko-hero__avatar">
            <KikoAvatar state={state} size={232} />
          </div>
        </section>

        {live.aiAvailable === false && live.aiMessage ? (
          <KikoErrorState message={live.aiMessage} />
        ) : null}

        <KikoCommandBar
          disabled={readOnly || live.apiOnline === false}
          onActivity={(change) =>
            setLocal((current) => ({ ...current, ...change }))
          }
        />

        <nav className="kiko-actions" aria-label="Ações rápidas">
          {QUICK_ACTIONS.map((action) => (
            <Link key={action.href} className="kiko-action" href={action.href}>
              <KikoIcon name={action.icon} size={26} />
              <strong>{action.title}</strong>
              <span>{action.text}</span>
            </Link>
          ))}
        </nav>

        <KikoEcosystem />
      </div>

      <KikoContextPanel live={live} variant="docked" />
    </div>
  );
}
