import { authFetch } from './auth-client';

export type CommercialPlan = {
  code: string;
  name: string;
  description: string;
  seat_limit: number;
  monthly_token_limit: number;
  automation_limit: number;
  storage_limit_mb: number;
  retention_days: number;
  integrations: string[];
  support_level: string;
};

export type Subscription = {
  id: string;
  workspace_id: string;
  plan: CommercialPlan;
  status: string;
  billing_provider: string | null;
  current_period_start: string;
  current_period_end: string;
  trial_ends_at: string | null;
  cancel_at_period_end: boolean;
  cancelled_at: string | null;
  ai_tokens_used: number;
  automation_runs_used: number;
  storage_bytes_used: number;
  billing_configuration_status: string;
  invoice_links: string[];
};

async function json<T>(response: Response): Promise<T> {
  if (!response.ok)
    throw new Error(`Commercial request failed (${response.status})`);
  return (await response.json()) as T;
}

export function listCommercialPlans(): Promise<CommercialPlan[]> {
  return authFetch('/api/v1/commercial/plans').then((response) =>
    json<CommercialPlan[]>(response),
  );
}

export function getSubscription(): Promise<Subscription> {
  return authFetch('/api/v1/commercial/subscription').then((response) =>
    json<Subscription>(response),
  );
}

export function cancelSubscription(): Promise<Subscription> {
  return authFetch('/api/v1/commercial/subscription/cancel', {
    method: 'POST',
  }).then((response) => json<Subscription>(response));
}
