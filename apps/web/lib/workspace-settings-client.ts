import { authFetch } from './auth-client';

export type WorkspaceSettings = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  sector: string | null;
  country: string | null;
  website: string | null;
  branding: Record<string, unknown>;
  retention_days: number;
  ai_monthly_token_limit: number | null;
  role: 'owner' | 'admin' | 'manager' | 'member' | 'viewer';
  members: Array<{
    id: string;
    user_id: string;
    email: string;
    full_name: string;
    role: string;
    created_at: string;
  }>;
};

async function json(response: Response): Promise<WorkspaceSettings> {
  if (!response.ok)
    throw new Error(`Workspace settings request failed (${response.status})`);
  return (await response.json()) as WorkspaceSettings;
}

export function getWorkspaceSettings(): Promise<WorkspaceSettings> {
  return authFetch('/api/v1/workspaces/settings').then(json);
}

export function updateWorkspaceSettings(
  value: WorkspaceSettings,
): Promise<WorkspaceSettings> {
  return authFetch('/api/v1/workspaces/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: value.name,
      description: value.description,
      sector: value.sector,
      country: value.country,
      website: value.website,
      branding: value.branding,
      retention_days: value.retention_days,
      ai_monthly_token_limit: value.ai_monthly_token_limit,
    }),
  }).then(json);
}
