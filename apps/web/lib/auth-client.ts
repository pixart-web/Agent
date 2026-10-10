import type { AccessTokenResponse, AuthResponse, User } from './auth-types';
import { apiBaseUrl } from './api-url';

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

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? 'Authentication request failed.';
  } catch {
    return 'Authentication request failed.';
  }
}

async function expectJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new AuthClientError(await errorMessage(response), response.status);
  }
  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/login`, {
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
): Promise<AuthResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/register`, {
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
  const result = await expectJson<AuthResponse>(response);
  accessToken = result.access_token;
  return result;
}

export async function verifyEmail(token: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/verify-email`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
  await expectJson<{ message: string }>(response);
}

export async function resendVerification(email: string): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/auth/resend-verification`,
    {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    },
  );
  await expectJson<{ message: string }>(response);
}

export async function requestPasswordReset(email: string): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/auth/password-reset/request`,
    {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    },
  );
  await expectJson<{ message: string }>(response);
}

export async function confirmPasswordReset(
  token: string,
  password: string,
): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/auth/password-reset/confirm`,
    {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, password }),
    },
  );
  await expectJson<{ message: string }>(response);
}

async function performRefresh(): Promise<string | null> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/auth/refresh`, {
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
    fetch(`${apiBaseUrl}${path}`, {
      ...init,
      credentials: 'include',
      headers: authorizedHeaders(init.headers),
    });

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

export async function logout(): Promise<void> {
  try {
    await fetch(`${apiBaseUrl}/api/v1/auth/logout`, {
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
}
