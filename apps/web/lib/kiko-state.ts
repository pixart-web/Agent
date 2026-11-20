/**
 * Kiko's visible state, derived only from real application signals (API health, local AI
 * availability, approvals, agent runs, planning commands) and from what the person is doing
 * on screen (typing, waiting for an answer). Nothing here invents progress or activity.
 */

export const KIKO_STATES = [
  'idle',
  'listening',
  'thinking',
  'planning',
  'executing',
  'waiting_approval',
  'success',
  'error',
  'offline',
  'sleeping',
] as const;

export type KikoState = (typeof KIKO_STATES)[number];

export type KikoSignals = {
  /** The API answered its health check (null while still checking). */
  apiOnline: boolean | null;
  /** The local AI runtime and model are ready (null when unknown). */
  aiAvailable: boolean | null;
  pendingApprovals: number;
  activeAgentRuns: number;
  planningCommands: number;
  /** The person is typing a request for Kiko. */
  listening?: boolean;
  /** A request from this screen is waiting for the API. */
  thinking?: boolean;
  /** Outcome of the last request from this screen, shown briefly. */
  outcome?: 'success' | 'error' | null;
  /** No interaction for a long time and nothing is running. */
  idleForMs?: number;
};

export const SLEEP_AFTER_MS = 5 * 60_000;

export function deriveKikoState(signals: KikoSignals): KikoState {
  if (signals.apiOnline === false) return 'offline';
  if (signals.thinking) return 'thinking';
  if (signals.outcome === 'error') return 'error';
  if (signals.outcome === 'success') return 'success';
  if (signals.listening) return 'listening';
  if (signals.aiAvailable === false) return 'error';
  if (signals.activeAgentRuns > 0) return 'executing';
  if (signals.pendingApprovals > 0) return 'waiting_approval';
  if (signals.planningCommands > 0) return 'planning';
  if ((signals.idleForMs ?? 0) >= SLEEP_AFTER_MS) return 'sleeping';
  return 'idle';
}

export const KIKO_STATE_COPY: Record<
  KikoState,
  { label: string; detail: string }
> = {
  idle: {
    label: 'Disponível',
    detail: 'Pronto para planear, executar e analisar contigo.',
  },
  listening: {
    label: 'A ouvir',
    detail: 'Escreve o que precisas e carrega em Enter.',
  },
  thinking: {
    label: 'A pensar',
    detail: 'A preparar a resposta com a IA local.',
  },
  planning: {
    label: 'A planear',
    detail: 'O Supervisor está a preparar um plano.',
  },
  executing: {
    label: 'A executar',
    detail: 'Há agentes a trabalhar em tarefas agora.',
  },
  waiting_approval: {
    label: 'À espera de aprovação',
    detail: 'Há ações que precisam da tua decisão.',
  },
  success: { label: 'Feito', detail: 'O pedido foi entregue.' },
  error: {
    label: 'Precisa de atenção',
    detail: 'A IA local não está disponível ou o pedido falhou.',
  },
  offline: {
    label: 'Sem ligação',
    detail: 'Não consigo contactar o servidor Kiko.',
  },
  sleeping: {
    label: 'Em repouso',
    detail: 'Sem atividade há algum tempo. Basta escreveres para acordar.',
  },
};

/** Greeting for the local time of day. */
export function greeting(date: Date): string {
  const hour = date.getHours();
  if (hour < 5) return 'Boa noite';
  if (hour < 12) return 'Bom dia';
  if (hour < 20) return 'Boa tarde';
  return 'Boa noite';
}

export function firstName(fullName: string | null | undefined): string {
  return (fullName ?? '').trim().split(/\s+/)[0] ?? '';
}
