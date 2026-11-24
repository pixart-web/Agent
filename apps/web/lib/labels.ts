/**
 * Portuguese (pt-PT) labels for values the API sends as identifiers: statuses, roles, risk
 * levels, priorities, triggers, knowledge categories and event kinds. Unknown values fall
 * back to a readable form of the identifier.
 */
const LABELS: Record<string, string> = {
  // Workflow, task, run and execution states
  pending: 'Pendente',
  planning: 'A planear',
  in_progress: 'Em curso',
  ready: 'Pronta',
  running: 'A decorrer',
  waiting_approval: 'À espera de aprovação',
  completed: 'Concluído',
  succeeded: 'Concluído',
  failed: 'Falhou',
  cancelled: 'Cancelado',
  blocked: 'Bloqueado',
  queued: 'Em fila',
  dispatched: 'Enviado',
  retry_scheduled: 'Nova tentativa agendada',
  delivery_unknown: 'Entrega incerta',
  skipped: 'Ignorado',
  created: 'Criado',
  proposed: 'Proposto',
  draft: 'Rascunho',
  approved: 'Aprovado',
  rejected: 'Rejeitado',
  expired: 'Expirado',
  superseded: 'Substituído',
  archived: 'Arquivado',
  active: 'Ativo',
  inactive: 'Inativo',
  paused: 'Em pausa',
  suspended: 'Suspenso',
  planned: 'Planeado',
  on_hold: 'Em espera',
  scheduled: 'Agendado',
  published: 'Publicado',
  in_review: 'Em revisão',
  idea: 'Ideia',
  open: 'Aberto',
  won: 'Ganho',
  lost: 'Perdido',
  trialing: 'Em período experimental',
  past_due: 'Pagamento em atraso',
  unread: 'Por ler',
  read: 'Lida',
  connected: 'Ligado',
  not_connected: 'Por ligar',
  disconnected: 'Desligado',
  revoked: 'Revogado',
  degraded: 'Com problemas',
  disabled: 'Desativado',
  enabled: 'Ativo',
  confirmed: 'Confirmado',
  tentative: 'Provisório',
  // Agents
  supervisor: 'Supervisor',
  marketing: 'Marketing',
  sales: 'Vendas',
  support: 'Suporte',
  development: 'Desenvolvimento',
  // Workspace roles
  owner: 'Dono',
  admin: 'Administrador',
  manager: 'Gestor',
  member: 'Membro',
  viewer: 'Leitura',
  // Risk and priority
  green: 'Verde',
  yellow: 'Amarelo',
  red: 'Vermelho',
  low: 'Baixa',
  normal: 'Normal',
  high: 'Alta',
  urgent: 'Urgente',
  // Automation triggers
  manual: 'Manual',
  schedule: 'Agendamento',
  webhook: 'Webhook',
  crm_change: 'Alteração no CRM',
  email_received: 'Email recebido',
  calendar_event: 'Evento de calendário',
  task_state: 'Estado da tarefa',
  // Knowledge
  company_profile: 'Perfil da empresa',
  approved_knowledge: 'Conhecimento aprovado',
  service: 'Serviço',
  product: 'Produto',
  policy: 'Política',
  procedure: 'Procedimento',
  brand_guideline: 'Diretriz de marca',
  general: 'Geral',
  internal: 'Interno',
  confidential: 'Confidencial',
  public: 'Público',
  restricted: 'Restrito',
  // Notification and history events
  approval_required: 'Aprovação necessária',
  approval_requested: 'Aprovação pedida',
  approval_decided: 'Aprovação decidida',
  plan_approved: 'Plano aprovado',
  plan_ready: 'Plano pronto',
  execution_failed: 'Execução falhou',
  task_failed: 'Tarefa falhou',
  commented: 'Comentário',
  comment: 'Comentário',
};

export function label(value: string | null | undefined): string {
  if (!value) return '';
  const known = LABELS[value] ?? LABELS[value.toLowerCase()];
  if (known) return known;
  const readable = value.replaceAll('_', ' ');
  return readable.charAt(0).toUpperCase() + readable.slice(1);
}

/** Portuguese for the local-AI status messages the API reports on agent overviews. */
export function operationalMessage(message: string | null | undefined): string {
  if (!message) return '';
  const ready = /^Local model (.+) ready$/.exec(message);
  if (ready) return `Modelo local ${ready[1]} pronto`;
  const missing = /^Local model (.+) is not installed$/.exec(message);
  if (missing) return `O modelo local ${missing[1]} não está instalado`;
  if (message === 'Local AI runtime is not reachable')
    return 'A IA local não está a responder';
  if (message === 'Sandbox provider configured')
    return 'Fornecedor de testes configurado';
  if (message === 'Agent disabled for this workspace')
    return 'Agente desativado neste workspace';
  return message;
}
