export const AGENT_CATALOG = [
  {
    id: 'supervisor',
    name: 'Supervisor',
    description:
      'Coordinates priorities, delegates work, and tracks execution.',
  },
  {
    id: 'marketing',
    name: 'Marketing',
    description: 'Supports campaigns, content operations, and brand workflows.',
  },
  {
    id: 'sales',
    name: 'Sales',
    description:
      'Assists pipeline management, proposals, and commercial follow-up.',
  },
  {
    id: 'support',
    name: 'Support',
    description:
      'Helps resolve customer requests and organize service knowledge.',
  },
  {
    id: 'development',
    name: 'Development',
    description:
      'Supports engineering delivery, quality, and technical operations.',
  },
] as const;

export type AgentId = (typeof AGENT_CATALOG)[number]['id'];

export const COMMAND_STATUSES = [
  'pending',
  'planning',
  'in_progress',
  'completed',
  'failed',
  'cancelled',
] as const;

export const PLAN_STATUSES = [
  'draft',
  'ready',
  'in_progress',
  'completed',
  'failed',
  'cancelled',
] as const;

export const TASK_STATUSES = [
  'pending',
  'ready',
  'running',
  'waiting_approval',
  'completed',
  'failed',
  'cancelled',
  'blocked',
] as const;

export const TASK_PRIORITIES = ['low', 'normal', 'high', 'urgent'] as const;
export const RISK_LEVELS = ['green', 'yellow', 'red'] as const;

export type CommandStatus = (typeof COMMAND_STATUSES)[number];
export type PlanStatus = (typeof PLAN_STATUSES)[number];
export type TaskStatus = (typeof TASK_STATUSES)[number];
export type TaskPriority = (typeof TASK_PRIORITIES)[number];
export type RiskLevel = (typeof RISK_LEVELS)[number];

export type Command = {
  id: string;
  user_id: string;
  input: string;
  status: CommandStatus;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

export type Plan = {
  id: string;
  command_id: string;
  title: string;
  objective: string;
  status: PlanStatus;
  created_at: string;
  updated_at: string;
};

export type WorkflowTask = {
  id: string;
  plan_id: string;
  agent_id: AgentId;
  title: string;
  instructions: string;
  status: TaskStatus;
  priority: TaskPriority;
  risk_level: RiskLevel;
  sequence: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
};

export type TaskStatusHistory = {
  id: string;
  task_id: string;
  from_status: TaskStatus | null;
  to_status: TaskStatus;
  changed_by_user_id: string | null;
  reason: string | null;
  created_at: string;
};

export type TaskDetail = WorkflowTask & {
  history: TaskStatusHistory[];
};

export const TASK_TRANSITIONS: Record<TaskStatus, readonly TaskStatus[]> = {
  pending: ['ready', 'cancelled'],
  ready: ['running', 'cancelled', 'blocked'],
  running: ['completed', 'failed', 'waiting_approval', 'blocked'],
  waiting_approval: ['ready', 'cancelled'],
  blocked: ['ready', 'cancelled'],
  failed: ['ready', 'cancelled'],
  completed: [],
  cancelled: [],
};
