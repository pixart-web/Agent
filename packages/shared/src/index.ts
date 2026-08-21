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
  version: number;
  is_current: boolean;
  title: string;
  objective: string;
  reasoning_summary: string | null;
  rejection_reason: string | null;
  status: PlanStatus;
  created_at: string;
  updated_at: string;
  approved_at: string | null;
  approved_by_user_id: string | null;
};

export type SupervisorRunStatus =
  'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export type SupervisorRun = {
  id: string;
  command_id: string;
  user_id: string;
  status: SupervisorRunStatus;
  provider: string;
  model: string;
  prompt_version: string;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  estimated_cost: string | null;
  currency: string | null;
  latency_ms: number | null;
  request_id: string | null;
  error_code: string | null;
  error_message: string | null;
  user_feedback: string | null;
  created_at: string;
  completed_at: string | null;
};

export type SupervisorPlanResponse = {
  plan: Plan;
  tasks: WorkflowTask[];
  run: SupervisorRun;
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

export type TaskActionStatus =
  | 'proposed'
  | 'waiting_approval'
  | 'approved'
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type TaskExecutionStatus =
  | 'created'
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'retry_scheduled'
  | 'cancelled'
  | 'waiting_approval';

export type ApprovalStatus =
  'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled';

export type ActorType =
  'user' | 'kiko' | 'supervisor' | 'agent' | 'worker' | 'system';

export type TaskAction = {
  id: string;
  task_id: string;
  tool_name: string;
  tool_version: string;
  input_payload: Record<string, unknown>;
  risk_level: RiskLevel;
  status: TaskActionStatus;
  created_by_type: ActorType;
  created_by_id: string | null;
  action_fingerprint: string;
  correlation_id: string;
  created_at: string;
  updated_at: string;
};

export type TaskExecution = {
  id: string;
  task_id: string;
  task_action_id: string;
  attempt_number: number;
  status: TaskExecutionStatus;
  tool_name: string;
  tool_version: string;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown> | null;
  error_code: string | null;
  error_message: string | null;
  queued_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  worker_id: string | null;
  duration_ms: number | null;
  correlation_id: string;
  created_at: string;
  updated_at: string;
};

export type ApprovalRequest = {
  id: string;
  user_id: string;
  task_id: string;
  task_action_id: string;
  risk_level: RiskLevel;
  title: string;
  description: string;
  status: ApprovalStatus;
  action_fingerprint: string;
  requested_at: string;
  decided_at: string | null;
  decided_by_user_id: string | null;
  decision_reason: string | null;
  expires_at: string | null;
  correlation_id: string;
};

export type DispatchResponse = {
  action: TaskAction;
  execution: TaskExecution | null;
  approval: ApprovalRequest | null;
};

export type AuditLog = {
  id: string;
  actor_type: ActorType;
  actor_id: string | null;
  event_type: string;
  resource_type: string;
  resource_id: string;
  metadata_payload: Record<string, unknown>;
  created_at: string;
  correlation_id: string;
};

export type PlanProgress = {
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  running_tasks: number;
  waiting_approval_tasks: number;
  progress_percentage: number;
};

export type AgentRunStatus =
  'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export type AgentRun = {
  id: string;
  task_id: string;
  agent_id: string;
  user_id: string;
  status: AgentRunStatus;
  provider: string;
  model: string;
  prompt_version: string;
  user_feedback: string | null;
  proposal_summary: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  latency_ms: number | null;
  error_code: string | null;
  error_message: string | null;
  correlation_id: string;
  created_at: string;
  completed_at: string | null;
};

export type AgentRunResponse = { run: AgentRun; actions: TaskAction[] };

export type AgentCapabilities = {
  id: string;
  name: string;
  description: string;
  prompt_version: string;
  allowed_tools: string[];
  default_risk_policy: RiskLevel;
  max_actions: number;
};

export type AgentOverview = {
  capabilities: AgentCapabilities;
  tasks_pending: number;
  tasks_running: number;
  tasks_waiting_approval: number;
  tasks_failed: number;
  recent_runs: AgentRun[];
  completed_runs: number;
  failed_runs: number;
  success_rate: number;
};

export type GitHubIntegrationStatus = {
  enabled: boolean;
  allowed_repositories: string[];
  credential_configured: boolean;
};
