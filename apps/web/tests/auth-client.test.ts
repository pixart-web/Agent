import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  authFetch,
  clearAuthState,
  login,
  logout,
  refreshAccessToken,
} from '../lib/auth-client';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('auth client', () => {
  beforeEach(() => {
    clearAuthState();
    vi.unstubAllGlobals();
  });

  it('clears the in-memory access token on logout', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: 'memory-token',
          token_type: 'bearer',
          user: {},
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response(null, { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await login('user@example.com', 'securePassword123');
    await logout();
    await authFetch('/health', {}, false);

    const finalHeaders = new Headers(fetchMock.mock.calls[2][1]?.headers);
    expect(finalHeaders.has('Authorization')).toBe(false);
  });

  it('does not loop after a failed refresh', async () => {
    const unauthorized = new Response(null, { status: 401 });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(unauthorized)
      .mockResolvedValueOnce(new Response(null, { status: 401 }));
    vi.stubGlobal('fetch', fetchMock);

    const response = await authFetch('/api/v1/auth/me');

    expect(response.status).toBe(401);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('treats an unavailable refresh API as a failed session', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('offline'));
    vi.stubGlobal('fetch', fetchMock);

    await expect(refreshAccessToken()).resolves.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('shares one refresh request across concurrent callers', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        access_token: 'new-token',
        token_type: 'bearer',
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const [first, second] = await Promise.all([
      refreshAccessToken(),
      refreshAccessToken(),
    ]);

    expect(first).toBe('new-token');
    expect(second).toBe('new-token');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
