import { saveDownload } from './downloads';
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
  is_synthetic_demo: boolean;
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
    throw new Error(
      `O pedido das definições do workspace falhou (${response.status})`,
    );
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

export async function downloadWorkspaceExport(
  resource:
    | 'all'
    | 'organizations'
    | 'contacts'
    | 'projects'
    | 'tasks'
    | 'activities' = 'all',
  format: 'json' | 'csv' = 'json',
): Promise<void> {
  const response = await authFetch(
    `/api/v1/data-portability/export?resource=${resource}&format=${format}`,
  );
  if (!response.ok)
    throw new Error(`A exportação do workspace falhou (${response.status})`);
  const disposition = response.headers.get('content-disposition') ?? '';
  const filename =
    disposition.match(/filename="([^"]+)"/)?.[1] ??
    `kiko-workspace-export.${format}`;
  await saveDownload(await response.blob(), filename);
}

/** Make another workspace the active one for this account. */
export async function switchWorkspace(workspaceId: string): Promise<void> {
  const response = await authFetch('/api/v1/workspaces/switch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workspace_id: workspaceId }),
  });
  if (!response.ok)
    throw new Error(`Não foi possível mudar de workspace (${response.status})`);
}
