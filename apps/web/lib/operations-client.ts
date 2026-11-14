import { authFetch } from './auth-client';

export type RecentExecution = {
  id: string;
  task_id: string;
  tool_name: string;
  status: string;
  duration_ms: number | null;
  created_at: string;
};

export type OperationsOverview = {
  active_commands: number;
  pending_tasks: number;
  pending_approvals: number;
  active_agent_runs: number;
  enabled_automations: number;
  connected_integrations: number;
  unread_alerts: number;
  recent_executions: RecentExecution[];
};

export type OperationsAnalytics = {
  period_days: number;
  totals: {
    commands: number;
    agent_runs: number;
    tool_executions: number;
    successful_tool_executions: number;
    failed_tool_executions: number;
    total_tokens: number;
    automation_runs: number;
    successful_automation_runs: number;
    failed_automation_runs: number;
  };
  estimated_cost_minor: number | null;
  estimated_cost_currency: string | null;
  cost_status: string;
  trends: Array<{
    date: string;
    commands: number;
    agent_runs: number;
    tool_executions: number;
    automation_runs: number;
  }>;
};

async function json<T>(response: Response): Promise<T> {
  if (!response.ok)
    throw new Error(`Operations request failed (${response.status})`);
  return (await response.json()) as T;
}

export function getOperationsOverview(): Promise<OperationsOverview> {
  return authFetch('/api/v1/operations/overview').then((response) =>
    json<OperationsOverview>(response),
  );
}

export function getOperationsAnalytics(
  days = 30,
): Promise<OperationsAnalytics> {
  return authFetch(`/api/v1/operations/analytics?days=${days}`).then(
    (response) => json<OperationsAnalytics>(response),
  );
}
