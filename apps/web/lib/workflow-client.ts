import type {
  AgentId,
  Command,
  CommandStatus,
  Plan,
  RiskLevel,
  TaskDetail,
  TaskPriority,
  TaskStatus,
  WorkflowTask,
} from '@agent/shared';

import { authFetch } from './auth-client';

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

export function listAgents(): Promise<Agent[]> {
  return request('/api/v1/agents');
}
