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

export type CodexRunStatus =
  | 'created'
  | 'waiting_approval'
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancelled';

export type CodexRun = {
  id: string;
  task_id: string;
  task_action_id: string;
  repository: string;
  base_branch: string;
  working_branch: string | null;
  status: CodexRunStatus;
  instruction: string;
  acceptance_criteria: string[];
  runner_type: string;
  model: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  exit_code: number | null;
  summary: string | null;
  error_code: string | null;
  error_message: string | null;
  files_changed: string[];
  tests_run: string[];
  tests_passed: boolean | null;
  commit_sha: string | null;
  pull_request_number: number | null;
  pull_request_url: string | null;
  correlation_id: string;
  created_at: string;
  updated_at: string;
};

export type CodexIntegrationStatus = {
  enabled: boolean;
  runner: string;
  allowed_repositories: string[];
  credential_configured: boolean;
  github_credential_configured: boolean;
  timeout_seconds: number;
};

export type EmailAddress = { address: string; name: string | null };
export type EmailAttachmentMetadata = {
  attachment_id: string | null;
  filename: string;
  mime_type: string;
  size: number;
  blocked: boolean;
};
export type EmailMessageSummary = {
  id: string;
  thread_id: string;
  subject: string;
  sender: EmailAddress;
  recipients: EmailAddress[];
  sent_at: string | null;
  snippet: string;
  unread: boolean;
  has_attachments: boolean;
  external_content: true;
  trust: 'untrusted';
};
export type EmailMessage = EmailMessageSummary & {
  cc: EmailAddress[];
  reply_to: EmailAddress[];
  text_body: string;
  body_truncated: boolean;
  attachments: EmailAttachmentMetadata[];
  provider_headers: Record<string, string>;
};
export type EmailAccount = {
  id: string;
  provider: string;
  account_type: string;
  email_address: string;
  status: string;
  scopes: string[];
  last_sync_at: string | null;
};
export type EmailIntegrationStatus = {
  enabled: boolean;
  provider: string;
  send_enabled: boolean;
  mark_read_enabled: boolean;
  connected_accounts: number;
};

export type CalendarAccount = EmailAccount;
export type CalendarIntegrationStatus = {
  enabled: boolean;
  provider: string;
  write_enabled: boolean;
  connected_accounts: number;
};
export type CalendarEventTime = {
  date_time: string | null;
  date: string | null;
  time_zone: string | null;
};
export type CalendarInfo = {
  id: string;
  summary: string;
  description: string;
  time_zone: string;
  primary: boolean;
  access_role: string;
  external_content: true;
  trust: 'untrusted';
};
export type CalendarAttendee = {
  email: string;
  display_name: string | null;
  response_status: string | null;
  optional: boolean;
  external: boolean;
};
export type CalendarEvent = {
  id: string;
  calendar_id: string;
  title: string;
  description: string;
  location: string;
  start: CalendarEventTime;
  end: CalendarEventTime;
  status: string;
  attendees: CalendarAttendee[];
  recurrence: string[];
  conference_url: string | null;
  html_link: string | null;
  organizer_email: string | null;
  updated_at: string | null;
  external_content: true;
  trust: 'untrusted';
};

export type CrmContactMethod = {
  id: string;
  method_type: 'email' | 'phone';
  value: string;
  label: string | null;
  is_primary: boolean;
};
export type CrmAddress = {
  id: string;
  kind: string;
  line1: string;
  line2: string | null;
  city: string;
  region: string | null;
  postal_code: string | null;
  country_code: string;
};
export type CrmContact = {
  id: string;
  organization_id: string | null;
  full_name: string;
  job_title: string | null;
  website: string | null;
  status: string;
  source: string;
  methods: CrmContactMethod[];
  addresses: CrmAddress[];
  tags: string[];
  created_at: string;
  updated_at: string;
};
export type CrmOrganization = {
  id: string;
  name: string;
  website: string | null;
  status: string;
  source: string;
  addresses: CrmAddress[];
  tags: string[];
  member_count: number;
  created_at: string;
  updated_at: string;
};
export type CrmActivity = {
  id: string;
  contact_id: string | null;
  organization_id: string | null;
  activity_type: string;
  subject: string;
  details: Record<string, unknown>;
  source: string;
  occurred_at: string;
  email_reference_id: string | null;
  calendar_reference_id: string | null;
};

export type CrmClient = {
  id: string;
  organization: CrmOrganization;
  owner_user_id: string;
  lifecycle_status: string;
  industry: string | null;
  summary: string | null;
  created_at: string;
  updated_at: string;
};
export type CrmProject = {
  id: string;
  client_id: string;
  owner_user_id: string;
  name: string;
  description: string | null;
  status: string;
  starts_on: string | null;
  due_on: string | null;
  created_at: string;
  updated_at: string;
};
export type CrmOpportunity = {
  id: string;
  client_id: string;
  contact_id: string | null;
  pipeline_id: string;
  stage_id: string;
  owner_user_id: string;
  title: string;
  description: string | null;
  amount_minor: number;
  currency: string;
  probability: number;
  status: string;
  expected_close_on: string | null;
  created_at: string;
  updated_at: string;
};
export type CrmTaskSummary = {
  id: string;
  project_id: string | null;
  title: string;
  status: string;
  agent_id: string;
  created_at: string;
};
export type CrmNote = {
  id: string;
  contact_id: string | null;
  organization_id: string | null;
  body: string;
  source: string;
  created_at: string;
};
export type CrmHistory = {
  id: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  changes: Record<string, unknown>;
  created_at: string;
};
export type CrmInsight = {
  kind: 'fact' | 'model_summary';
  provenance: 'system_fact' | 'llm';
  text: string;
  generated_at: string | null;
};
export type CrmClient360 = {
  client: CrmClient;
  contacts: CrmContact[];
  emails: CrmActivity[];
  meetings: CrmActivity[];
  projects: CrmProject[];
  tasks: CrmTaskSummary[];
  activities: CrmActivity[];
  opportunities: CrmOpportunity[];
  notes: CrmNote[];
  history: CrmHistory[];
  insights: CrmInsight[];
};

export type MarketingCampaign = {
  id: string;
  client_id: string | null;
  owner_user_id: string;
  name: string;
  objective: string;
  status: string;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
  updated_at: string;
};
export type MarketingContent = {
  id: string;
  campaign_id: string;
  task_id: string | null;
  content_type: string;
  channel: string;
  title: string;
  body: string;
  lifecycle_status: string;
  scheduled_for: string | null;
  created_at: string;
  updated_at: string;
};
export type MarketingContentHistory = {
  id: string;
  from_status: string | null;
  to_status: string;
  reason: string | null;
  created_at: string;
};
export type MarketingAsset = {
  id: string;
  campaign_id: string | null;
  content_id: string | null;
  name: string;
  media_type: string;
  locator: string;
  metadata: Record<string, unknown>;
  created_at: string;
};
export type MarketingPublication = {
  id: string;
  content_id: string;
  channel: string;
  external_reference: string;
  published_at: string;
  created_at: string;
};
export type MarketingMetric = {
  id: string;
  campaign_id: string | null;
  content_id: string | null;
  metric_name: string;
  value: number;
  source: string;
  measured_at: string;
  metadata: Record<string, unknown>;
  created_at: string;
};
export type MarketingContentDetail = {
  content: MarketingContent;
  history: MarketingContentHistory[];
  assets: MarketingAsset[];
  publications: MarketingPublication[];
  metrics: MarketingMetric[];
};

export type AutomationTriggerType =
  | 'schedule'
  | 'email_received'
  | 'calendar_event'
  | 'crm_change'
  | 'task_state'
  | 'manual'
  | 'webhook';
export type AutomationCondition = {
  field: string;
  operator: 'eq' | 'not_eq' | 'in' | 'exists';
  value: unknown;
};
export type Automation = {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  trigger_type: AutomationTriggerType;
  trigger_config: Record<string, unknown>;
  conditions: AutomationCondition[];
  command_template: string;
  max_depth: number;
  max_runs_per_window: number;
  window_seconds: number;
  cooldown_seconds: number;
  next_run_at: string | null;
  last_triggered_at: string | null;
  created_at: string;
  updated_at: string;
};
export type AutomationRun = {
  id: string;
  automation_id: string;
  trigger_type: AutomationTriggerType;
  trigger_key: string;
  status: 'running' | 'completed' | 'skipped' | 'failed';
  correlation_id: string;
  causation_run_id: string | null;
  depth: number;
  command_id: string | null;
  skipped_reason: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  deduplicated: boolean;
};
