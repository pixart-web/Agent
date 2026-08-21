import type {
  CodexIntegrationStatus,
  CodexRun,
  CodexRunStatus,
} from '@agent/shared';
import type {
  AgentOverview,
  AgentRun,
  AgentRunResponse,
  GitHubIntegrationStatus,
} from '@agent/shared';
import type {
  AgentId,
  Command,
  CommandStatus,
  Plan,
  RiskLevel,
  SupervisorPlanResponse,
  SupervisorRun,
  TaskDetail,
  TaskPriority,
  TaskStatus,
  WorkflowTask,
} from '@agent/shared';

import { authFetch } from './auth-client';
import type {
  ApprovalRequest,
  ApprovalStatus,
  AuditLog,
  DispatchResponse,
  PlanProgress,
  TaskAction,
  TaskExecution,
  TaskExecutionStatus,
} from '@agent/shared';

export type Agent = {
  id: AgentId;
  name: string;
  description: string;
  status: string;
};

export class WorkflowApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await authFetch(path, init);
  if (!response.ok) {
    let message = 'Workflow request failed.';
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail ?? message;
    } catch {
      // Preserve the safe generic message for non-JSON failures.
    }
    throw new WorkflowApiError(message, response.status);
  }
  return (await response.json()) as T;
}

function jsonRequest(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

export function createCommand(input: string): Promise<Command> {
  return request('/api/v1/commands', jsonRequest('POST', { input }));
}

export function listCommands(
  options: {
    limit?: number;
    offset?: number;
    status?: CommandStatus;
  } = {},
): Promise<Command[]> {
  const query = new URLSearchParams();
  if (options.limit !== undefined) query.set('limit', String(options.limit));
  if (options.offset !== undefined) query.set('offset', String(options.offset));
  if (options.status !== undefined) query.set('status', options.status);
  const suffix = query.size > 0 ? `?${query.toString()}` : '';
  return request(`/api/v1/commands${suffix}`);
}

export function getCommand(commandId: string): Promise<Command> {
  return request(`/api/v1/commands/${commandId}`);
}

export function cancelCommand(commandId: string): Promise<Command> {
  return request(`/api/v1/commands/${commandId}/cancel`, { method: 'POST' });
}

export function createPlan(
  commandId: string,
  data: { title: string; objective: string },
): Promise<Plan> {
  return request(
    `/api/v1/commands/${commandId}/plan`,
    jsonRequest('POST', data),
  );
}

export function getPlan(commandId: string): Promise<Plan> {
  return request(`/api/v1/commands/${commandId}/plan`);
}

export function listPlans(commandId: string): Promise<Plan[]> {
  return request(`/api/v1/commands/${commandId}/plans`);
}

export function getPlanById(planId: string): Promise<Plan> {
  return request(`/api/v1/plans/${planId}`);
}

export function generateSupervisorPlan(
  commandId: string,
): Promise<SupervisorPlanResponse> {
  return request(`/api/v1/commands/${commandId}/generate-plan`, {
    method: 'POST',
  });
}

export function regenerateSupervisorPlan(
  commandId: string,
  feedback: string,
): Promise<SupervisorPlanResponse> {
  return request(
    `/api/v1/commands/${commandId}/regenerate-plan`,
    jsonRequest('POST', { feedback }),
  );
}

export function approvePlan(planId: string): Promise<Plan> {
  return request(`/api/v1/plans/${planId}/approve`, { method: 'POST' });
}

export function rejectPlan(planId: string, reason: string): Promise<Plan> {
  return request(
    `/api/v1/plans/${planId}/reject`,
    jsonRequest('POST', { reason }),
  );
}

export function listSupervisorRuns(
  commandId: string,
): Promise<SupervisorRun[]> {
  return request(`/api/v1/commands/${commandId}/supervisor-runs`);
}

export function createTask(
  planId: string,
  data: {
    agent_id: AgentId;
    title: string;
    instructions: string;
    priority: TaskPriority;
    risk_level: RiskLevel;
    sequence: number;
  },
): Promise<WorkflowTask> {
  return request(`/api/v1/plans/${planId}/tasks`, jsonRequest('POST', data));
}

export function listTasks(planId: string): Promise<WorkflowTask[]> {
  return request(`/api/v1/plans/${planId}/tasks`);
}

export function getTask(taskId: string): Promise<TaskDetail> {
  return request(`/api/v1/tasks/${taskId}`);
}

export function updateTask(
  taskId: string,
  data: Partial<
    Pick<
      WorkflowTask,
      | 'agent_id'
      | 'title'
      | 'instructions'
      | 'priority'
      | 'risk_level'
      | 'sequence'
    >
  >,
): Promise<WorkflowTask> {
  return request(`/api/v1/tasks/${taskId}`, jsonRequest('PATCH', data));
}

export function transitionTask(
  taskId: string,
  status: TaskStatus,
  reason?: string,
): Promise<TaskDetail> {
  return request(
    `/api/v1/tasks/${taskId}/transition`,
    jsonRequest('POST', { status, reason: reason || null }),
  );
}
export function createTaskAction(
  taskId: string,
  data: {
    tool_name: string;
    tool_version?: string;
    input_payload: Record<string, unknown>;
    risk_level?: RiskLevel;
  },
): Promise<TaskAction> {
  return request(`/api/v1/tasks/${taskId}/actions`, jsonRequest('POST', data));
}

export function listTaskActions(taskId: string): Promise<TaskAction[]> {
  return request(`/api/v1/tasks/${taskId}/actions`);
}

export function dispatchAction(actionId: string): Promise<DispatchResponse> {
  return request(`/api/v1/actions/${actionId}/dispatch`, { method: 'POST' });
}

export function cancelAction(actionId: string): Promise<TaskAction> {
  return request(`/api/v1/actions/${actionId}/cancel`, { method: 'POST' });
}

export function listActionExecutions(
  actionId: string,
): Promise<TaskExecution[]> {
  return request(`/api/v1/actions/${actionId}/executions`);
}

export function listExecutions(
  options: {
    status?: TaskExecutionStatus;
    agent?: string;
    risk?: RiskLevel;
  } = {},
): Promise<TaskExecution[]> {
  const query = new URLSearchParams();
  if (options.status) query.set('status', options.status);
  if (options.agent) query.set('agent', options.agent);
  if (options.risk) query.set('risk', options.risk);
  const suffix = query.size ? `?${query.toString()}` : '';
  return request(`/api/v1/executions${suffix}`);
}

export function listApprovals(
  options: { status?: ApprovalStatus; risk_level?: RiskLevel } = {},
): Promise<ApprovalRequest[]> {
  const query = new URLSearchParams();
  if (options.status) query.set('status', options.status);
  if (options.risk_level) query.set('risk_level', options.risk_level);
  const suffix = query.size ? `?${query.toString()}` : '';
  return request(`/api/v1/approvals${suffix}`);
}

export function approveAction(
  approvalId: string,
  confirmHighRisk: boolean,
  reason?: string,
): Promise<DispatchResponse> {
  return request(
    `/api/v1/approvals/${approvalId}/approve`,
    jsonRequest('POST', {
      confirm_high_risk: confirmHighRisk,
      reason: reason || null,
    }),
  );
}

export function rejectAction(
  approvalId: string,
  reason?: string,
): Promise<ApprovalRequest> {
  return request(
    `/api/v1/approvals/${approvalId}/reject`,
    jsonRequest('POST', { reason: reason || null }),
  );
}

export function getPlanProgress(planId: string): Promise<PlanProgress> {
  return request(`/api/v1/plans/${planId}/progress`);
}

export function listCommandActivity(commandId: string): Promise<AuditLog[]> {
  return request(`/api/v1/commands/${commandId}/activity`);
}

export function listAgents(): Promise<Agent[]> {
  return request('/api/v1/agents');
}

export function runAgent(taskId: string): Promise<AgentRunResponse> {
  return request('/api/v1/tasks/' + taskId + '/run-agent', {
    method: 'POST',
  });
}

export function rerunAgent(
  taskId: string,
  feedback?: string,
): Promise<AgentRunResponse> {
  return request(
    '/api/v1/tasks/' + taskId + '/rerun-agent',
    jsonRequest('POST', { feedback: feedback || null }),
  );
}

export function listAgentRuns(taskId: string): Promise<AgentRun[]> {
  return request('/api/v1/tasks/' + taskId + '/agent-runs');
}

export function getAgentOverview(agentId: string): Promise<AgentOverview> {
  return request('/api/v1/agents/' + agentId + '/overview');
}

export function reassignTaskAgent(
  taskId: string,
  agentId: string,
): Promise<WorkflowTask> {
  return request(
    '/api/v1/tasks/' + taskId + '/reassign-agent',
    jsonRequest('POST', { agent_id: agentId }),
  );
}

export function getGitHubIntegrationStatus(): Promise<GitHubIntegrationStatus> {
  return request('/api/v1/integrations/github/status');
}

export function getCodexIntegrationStatus(): Promise<CodexIntegrationStatus> {
  return request('/api/v1/integrations/codex/status');
}

export function listCodexRuns(
  options: { status?: CodexRunStatus; limit?: number; offset?: number } = {},
): Promise<CodexRun[]> {
  const query = new URLSearchParams();
  if (options.status) query.set('status', options.status);
  if (options.limit !== undefined) query.set('limit', String(options.limit));
  if (options.offset !== undefined) query.set('offset', String(options.offset));
  const suffix = query.size ? `?${query.toString()}` : '';
  return request(`/api/v1/codex/runs${suffix}`);
}

export function getCodexRun(runId: string): Promise<CodexRun> {
  return request(`/api/v1/codex/runs/${runId}`);
}
