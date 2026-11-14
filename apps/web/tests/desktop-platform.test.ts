import { beforeEach, describe, expect, it, vi } from 'vitest';

const invoke = vi.fn();
// Plain (non-spy) override for rejection cases: spies track promise settlement in a way
// Vitest reports as a test error when the promise rejects.
let rawInvoke: ((...args: unknown[]) => Promise<unknown>) | null = null;
vi.mock('@tauri-apps/api/core', () => ({
  invoke: (...args: unknown[]) => (rawInvoke ?? invoke)(...args),
}));
vi.mock('@tauri-apps/api/event', () => ({
  listen: vi.fn(async () => () => undefined),
}));

import { resolveRouteParams } from '../lib/route-params';
import {
  STATIC_PARAM_PLACEHOLDER,
  staticRouteParams,
} from '../lib/static-route-params';
import {
  CONNECTIVITY_EVENT,
  DesktopConnectionError,
  __test,
  desktopFetch,
  takePendingRoute,
} from '../lib/desktop-bridge';
import { isRestorableRoute } from '../lib/desktop-routes';
import {
  PALETTE_DESTINATIONS,
  filterDestinations,
  isExternalHref,
} from '../components/desktop-shell';

describe('desktop route params', () => {
  it('replaces the export placeholder with the last URL segment', () => {
    expect(
      resolveRouteParams(
        { id: STATIC_PARAM_PLACEHOLDER },
        '/dashboard/tasks/abc-123/',
      ),
    ).toEqual({ id: 'abc-123' });
  });

  it('decodes encoded identifiers and leaves real params untouched', () => {
    expect(
      resolveRouteParams(
        { client_id: STATIC_PARAM_PLACEHOLDER },
        '/dashboard/crm/clients/a%20b',
      ),
    ).toEqual({ client_id: 'a b' });
    expect(
      resolveRouteParams({ id: 'real' }, '/dashboard/tasks/other'),
    ).toEqual({
      id: 'real',
    });
  });

  it('keeps the placeholder when the URL has no concrete identifier', () => {
    expect(
      resolveRouteParams(
        { id: STATIC_PARAM_PLACEHOLDER },
        `/dashboard/tasks/${STATIC_PARAM_PLACEHOLDER}/`,
      ),
    ).toEqual({ id: STATIC_PARAM_PLACEHOLDER });
  });

  it('pre-renders placeholders only for the desktop export', () => {
    const previous = process.env.KIKO_STATIC_EXPORT;
    process.env.KIKO_STATIC_EXPORT = 'true';
    expect(staticRouteParams('id')).toEqual([{ id: STATIC_PARAM_PLACEHOLDER }]);
    process.env.KIKO_STATIC_EXPORT = 'false';
    expect(staticRouteParams('id')).toEqual([]);
    process.env.KIKO_STATIC_EXPORT = previous;
  });
});

describe('desktop bridge transport', () => {
  beforeEach(() => invoke.mockReset());

  it('asks the shell for the deep link that launched the app', async () => {
    invoke.mockResolvedValue('/verify-email/?token=abc');
    await expect(takePendingRoute()).resolves.toBe('/verify-email/?token=abc');
    expect(invoke).toHaveBeenCalledWith('take_pending_route');
  });

  it('round-trips binary data through base64', () => {
    const bytes = new Uint8Array([0, 1, 2, 250, 255]);
    expect(Array.from(__test.fromBase64(__test.toBase64(bytes)))).toEqual(
      Array.from(bytes),
    );
  });

  it('sends method, relative path, headers and body to the native proxy', async () => {
    invoke.mockResolvedValue({
      status: 201,
      headers: [['content-type', 'application/json']],
      bodyBase64: btoa('{"ok":true}'),
    });
    const response = await desktopFetch('/api/v1/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Plan' }),
    });
    expect(response.status).toBe(201);
    expect(await response.json()).toEqual({ ok: true });
    const [command, args] = invoke.mock.calls[0] as [
      string,
      {
        request: {
          method: string;
          path: string;
          headers: [string, string][];
          bodyBase64: string;
        };
      },
    ];
    expect(command).toBe('api_request');
    expect(args.request.method).toBe('POST');
    expect(args.request.path).toBe('/api/v1/tasks');
    expect(atob(args.request.bodyBase64)).toBe('{"title":"Plan"}');
    expect(args.request.headers).toContainEqual([
      'content-type',
      'application/json',
    ]);
  });

  it('serialises multipart uploads with their boundary', async () => {
    invoke.mockResolvedValue({ status: 200, headers: [], bodyBase64: '' });
    const form = new FormData();
    form.set('upload', new Blob(['a,b\n1,2'], { type: 'text/csv' }), 'x.csv');
    await desktopFetch('/api/v1/crm/import/preview', {
      method: 'POST',
      body: form,
    });
    const request = (
      invoke.mock.calls[0][1] as {
        request: { headers: [string, string][]; bodyBase64: string };
      }
    ).request;
    const contentType = request.headers.find(
      ([name]) => name === 'content-type',
    );
    expect(contentType?.[1]).toMatch(/^multipart\/form-data; boundary=/);
    expect(atob(request.bodyBase64)).toContain('a,b\n1,2');
  });

  it('returns null bodies for 204 responses', async () => {
    invoke.mockResolvedValue({ status: 204, headers: [], bodyBase64: '' });
    const response = await desktopFetch('/api/v1/auth/logout', {
      method: 'POST',
    });
    expect(response.status).toBe(204);
    expect(response.body).toBeNull();
  });

  it('reports offline errors as network failures and emits connectivity', async () => {
    rawInvoke = async () => {
      throw { kind: 'offline', message: 'unreachable' };
    };
    const target = new EventTarget();
    vi.stubGlobal('window', target);
    const events: boolean[] = [];
    target.addEventListener(CONNECTIVITY_EVENT, (event) => {
      events.push((event as CustomEvent<{ online: boolean }>).detail.online);
    });
    const failure = await desktopFetch('/api/v1/tasks').catch(
      (error: unknown) => error,
    );
    vi.unstubAllGlobals();
    rawInvoke = null;
    expect(failure).toBeInstanceOf(DesktopConnectionError);
    expect(failure).toBeInstanceOf(TypeError);
    expect((failure as DesktopConnectionError).kind).toBe('offline');
    expect(events).toEqual([false]);
  });
});

describe('desktop shell helpers', () => {
  it('only restores dashboard routes', () => {
    expect(isRestorableRoute('/dashboard/tasks/abc-1/')).toBe(true);
    expect(isRestorableRoute('/login/')).toBe(false);
    expect(isRestorableRoute('https://evil.example/')).toBe(false);
    expect(isRestorableRoute('/dashboard//evil')).toBe(false);
    expect(isRestorableRoute('/dashboard/<script>')).toBe(false);
  });

  it('filters palette destinations by label and keywords', () => {
    expect(filterDestinations('')).toHaveLength(PALETTE_DESTINATIONS.length);
    expect(filterDestinations('contacts').map((item) => item.label)).toEqual([
      'CRM',
    ]);
    expect(filterDestinations('zzzz')).toEqual([]);
  });

  it('detects links that must open outside the app', () => {
    expect(isExternalHref('https://pixart.pt')).toBe(true);
    expect(isExternalHref('mailto:hello@pixart.pt')).toBe(true);
    expect(isExternalHref('/dashboard/tasks')).toBe(false);
    expect(isExternalHref('#plans')).toBe(false);
  });
});
