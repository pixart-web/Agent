import { authFetch } from './auth-client';
import { apiError } from './api-messages';

export type PlatformOverview = {
  workspace_count: number;
  active_workspace_count: number;
  user_count: number;
  active_user_count: number;
  active_session_count: number;
  integration_account_count: number;
  failed_email_count: number;
  subscription_status: 'not_configured';
  providers: Array<{ provider: string; enabled: boolean; configured: boolean }>;
};

export type PlatformWorkspace = {
  id: string;
  name: string;
  slug: string;
  status: string;
  member_count: number;
  created_at: string;
};

export type PlatformUser = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  last_login_at: string | null;
};

async function json<T>(response: Response): Promise<T> {
  if (!response.ok)
    throw await apiError(
      response,
      `O pedido de administração da plataforma falhou (${response.status}).`,
    );
  return (await response.json()) as T;
}

export function getPlatformOverview(): Promise<PlatformOverview> {
  return authFetch('/api/v1/platform-admin/overview').then((response) =>
    json<PlatformOverview>(response),
  );
}

export async function listPlatformWorkspaces(): Promise<PlatformWorkspace[]> {
  const result = await json<{ workspaces: PlatformWorkspace[] }>(
    await authFetch('/api/v1/platform-admin/workspaces'),
  );
  return result.workspaces;
}

export async function listPlatformUsers(): Promise<PlatformUser[]> {
  const result = await json<{ users: PlatformUser[] }>(
    await authFetch('/api/v1/platform-admin/users'),
  );
  return result.users;
}

export function setPlatformWorkspaceStatus(
  id: string,
  status: 'active' | 'suspended',
): Promise<PlatformWorkspace> {
  return authFetch(`/api/v1/platform-admin/workspaces/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  }).then((response) => json<PlatformWorkspace>(response));
}

export function setPlatformUserStatus(
  id: string,
  isActive: boolean,
): Promise<PlatformUser> {
  return authFetch(`/api/v1/platform-admin/users/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_active: isActive }),
  }).then((response) => json<PlatformUser>(response));
}

export type PixartAppStatus =
  'unsupported' | 'requires_setup' | 'available' | 'unavailable';

export type PixartApp = {
  id: string;
  key: string;
  name: string;
  description: string | null;
  base_url: string | null;
  api_version: string | null;
  docs_url: string | null;
  status: PixartAppStatus;
  last_health_status: string | null;
  last_health_at: string | null;
};

export function listPixartApps(): Promise<PixartApp[]> {
  return authFetch('/api/v1/pixart-apps').then((response) =>
    json<PixartApp[]>(response),
  );
}

export function registerPixartApp(value: {
  key: string;
  name: string;
  description?: string | null;
  base_url?: string | null;
}): Promise<PixartApp> {
  return authFetch('/api/v1/platform-admin/pixart-apps', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(value),
  }).then((response) => json<PixartApp>(response));
}

export function updatePixartApp(
  id: string,
  value: Partial<
    Pick<
      PixartApp,
      | 'name'
      | 'description'
      | 'base_url'
      | 'api_version'
      | 'docs_url'
      | 'status'
    >
  >,
): Promise<PixartApp> {
  return authFetch(`/api/v1/platform-admin/pixart-apps/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(value),
  }).then((response) => json<PixartApp>(response));
}

export function checkPixartAppHealth(id: string): Promise<PixartApp> {
  return authFetch(`/api/v1/platform-admin/pixart-apps/${id}/health`, {
    method: 'POST',
  }).then((response) => json<PixartApp>(response));
}
