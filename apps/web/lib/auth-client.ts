import type { AccessTokenResponse, OnboardingState, User } from './auth-types';
import { apiBaseUrl } from './api-url';
import { clearDesktopSession, desktopFetch } from './desktop-bridge';
import { isDesktop } from './platform';

function webFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${apiBaseUrl}${path}`, { ...init, credentials: 'include' });
}

/**
 * Transport for every Kiko API call. Web: same-origin `fetch` with the refresh cookie.
 * Desktop: the native shell proxies the request and holds the credentials.
 */
export const apiFetch: (path: string, init?: RequestInit) => Promise<Response> =
  isDesktop ? desktopFetch : webFetch;

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export class AuthClientError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

type ValidationIssue = { msg?: string };

/** Human-readable message from a FastAPI error body (string or validation-issue list). */
export function describeErrorDetail(detail: unknown): string | null {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const first = (detail as ValidationIssue[]).find(
      (issue) => typeof issue?.msg === 'string',
    );
    if (first?.msg) return first.msg.replace(/^Value error, /, '');
  }
  return null;
}

// Portuguese for the authentication messages the API returns.
const AUTH_MESSAGES: Record<string, string> = {
  'Authentication required': 'É preciso entrar novamente.',
  'Authentication temporarily unavailable':
    'A autenticação está temporariamente indisponível. Tenta de novo daqui a pouco.',
  'Current password is incorrect': 'A palavra-passe atual está incorreta.',
  'Email verification required':
    'Confirma primeiro o teu email: segue o link de verificação que te enviámos.',
  'Inactive user': 'Esta conta está desativada.',
  'Insufficient permissions': 'Não tens permissões para esta ação.',
  'Invalid email or password': 'Email ou palavra-passe incorretos.',
  'Invalid or expired password reset token':
    'O link para repor a palavra-passe é inválido ou expirou.',
  'Invalid or expired verification token':
    'O link de verificação é inválido ou expirou.',
  'Origin not allowed': 'Este endereço não está autorizado a usar o Kiko.',
  'Session not found': 'A sessão terminou. Entra de novo.',
  'Too many authentication attempts':
    'Demasiadas tentativas. Espera um minuto e tenta de novo.',
};

export function authMessage(detail: string): string {
  return AUTH_MESSAGES[detail] ?? detail;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    const detail = describeErrorDetail(body.detail);
    return detail ? authMessage(detail) : 'O pedido de autenticação falhou.';
  } catch {
    return 'O pedido de autenticação falhou.';
  }
}

async function expectJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new AuthClientError(await errorMessage(response), response.status);
  }
  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<void> {
  const response = await apiFetch(`/api/v1/auth/login`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  await expectJson<{ message: string }>(response);
}

export async function register(
  fullName: string,
  email: string,
  password: string,
  termsAccepted: boolean,
  privacyAccepted: boolean,
): Promise<void> {
  const response = await apiFetch(`/api/v1/auth/register`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      full_name: fullName,
      email,
      password,
      terms_accepted: termsAccepted,
      privacy_accepted: privacyAccepted,
    }),
  });
  await expectJson<{ message: string }>(response);
}

export async function verifyEmail(token: string): Promise<void> {
  const response = await apiFetch(`/api/v1/auth/verify-email`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
  await expectJson<{ message: string }>(response);
}

export async function resendVerification(email: string): Promise<void> {
  const response = await apiFetch(`/api/v1/auth/resend-verification`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  await expectJson<{ message: string }>(response);
}

export async function requestPasswordReset(email: string): Promise<void> {
  const response = await apiFetch(`/api/v1/auth/password-reset/request`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  await expectJson<{ message: string }>(response);
}

export async function confirmPasswordReset(
  token: string,
  password: string,
): Promise<void> {
  const response = await apiFetch(`/api/v1/auth/password-reset/confirm`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, password }),
  });
  await expectJson<{ message: string }>(response);
}

async function performRefresh(): Promise<string | null> {
  try {
    const response = await apiFetch(`/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });
    if (!response.ok) {
      accessToken = null;
      return null;
    }
    const result = (await response.json()) as AccessTokenResponse;
    accessToken = result.access_token;
    return accessToken;
  } catch {
    accessToken = null;
    return null;
  }
}

export function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise === null) {
    refreshPromise = performRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

function authorizedHeaders(headers: HeadersInit | undefined): Headers {
  const result = new Headers(headers);
  if (accessToken) {
    result.set('Authorization', `Bearer ${accessToken}`);
  }
  return result;
}

export async function authFetch(
  path: string,
  init: RequestInit = {},
  retryAfterRefresh = true,
): Promise<Response> {
  const send = () =>
    apiFetch(path, {
      ...init,
      credentials: 'include',
      headers: authorizedHeaders(init.headers),
    });

  // No token in memory yet (the page was just loaded): renew the session first instead of
  // sending a request that can only answer 401. The desktop app keeps its session natively.
  if (!isDesktop && accessToken === null && retryAfterRefresh) {
    const renewed = await refreshAccessToken();
    return renewed ? authFetch(path, init, false) : send();
  }

  const response = await send();
  if (response.status !== 401 || !retryAfterRefresh) {
    return response;
  }

  const refreshed = await refreshAccessToken();
  if (!refreshed) {
    return response;
  }
  return authFetch(path, init, false);
}

export async function getCurrentUser(): Promise<User | null> {
  const response = await authFetch('/api/v1/auth/me');
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as User;
}

export async function getOnboarding(): Promise<OnboardingState> {
  const response = await authFetch('/api/v1/workspaces/onboarding');
  return expectJson<OnboardingState>(response);
}

export async function updateOnboarding(value: {
  step: number;
  company_name?: string;
  company_description?: string;
  primary_objectives?: string[];
  complete?: boolean;
}): Promise<OnboardingState> {
  const response = await authFetch('/api/v1/workspaces/onboarding', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(value),
  });
  return expectJson<OnboardingState>(response);
}

export async function updateProfile(
  fullName: string,
  language = 'en',
  timezone = 'UTC',
): Promise<User> {
  const response = await authFetch('/api/v1/auth/me', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ full_name: fullName, language, timezone }),
  });
  return expectJson<User>(response);
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const response = await authFetch('/api/v1/auth/password/change', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  if (!response.ok) {
    throw new AuthClientError(await errorMessage(response), response.status);
  }
  clearAuthState();
}

export async function listSessions(): Promise<
  import('./auth-types').Session[]
> {
  const response = await authFetch('/api/v1/auth/sessions');
  return expectJson<import('./auth-types').Session[]>(response);
}

export async function revokeSession(id: string): Promise<void> {
  const response = await authFetch(`/api/v1/auth/sessions/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new AuthClientError(await errorMessage(response), response.status);
  }
}

export async function acceptWorkspaceInvitation(token: string): Promise<void> {
  const response = await authFetch('/api/v1/workspaces/invitations/accept', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
  await expectJson(response);
}

export async function logout(): Promise<void> {
  try {
    await apiFetch(`/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
  } finally {
    clearAuthState();
  }
}

export function clearAuthState(): void {
  accessToken = null;
  refreshPromise = null;
  if (isDesktop) void clearDesktopSession().catch(() => undefined);
}
