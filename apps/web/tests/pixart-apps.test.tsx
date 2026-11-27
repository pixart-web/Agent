import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PixartAppsAdmin } from '../components/pixart-apps-admin';
import { label } from '../lib/labels';
import {
  registerPixartApp,
  updatePixartApp,
} from '../lib/platform-admin-client';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('Pixart products registry', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('explains the contract rule and starts empty', () => {
    const html = renderToStaticMarkup(<PixartAppsAdmin />);
    expect(html).toContain('Produtos Pixart');
    expect(html).toContain('contrato da API');
    expect(html).toContain('Ainda não há produtos registados.');
  });

  it('labels every registry status in Portuguese', () => {
    expect(label('unsupported')).toBe('Sem contrato verificado');
    expect(label('requires_setup')).toBe('Requer configuração');
    expect(label('available')).toBe('Disponível');
    expect(label('unreachable')).toBe('Sem resposta');
  });

  it('registers a product and reports the contract rule in Portuguese', async () => {
    // authFetch renews the session first when no token is in memory.
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.includes('/auth/refresh'))
        return jsonResponse({ access_token: 'token', token_type: 'bearer' });
      if (init?.method === 'POST')
        return jsonResponse({ id: 'a1', key: 'nodera', name: 'Nodera' }, 201);
      return jsonResponse(
        {
          detail:
            'Record the API address, version and documentation before marking it available',
        },
        409,
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    await registerPixartApp({ key: 'nodera', name: 'Nodera' });
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).endsWith('/api/v1/platform-admin/pixart-apps'),
      ),
    ).toBe(true);
    await expect(
      updatePixartApp('a1', { status: 'available' }),
    ).rejects.toThrow(
      'Regista o endereço, a versão e a documentação da API antes de o marcar como disponível.',
    );
  });
});
