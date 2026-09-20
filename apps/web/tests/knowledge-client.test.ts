import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  createKnowledge,
  createWorkspace,
  searchKnowledge,
} from '../lib/knowledge-client';

afterEach(() => vi.unstubAllGlobals());

describe('knowledge client', () => {
  it('creates a workspace with the requested scoped identity', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ id: 'w1', name: 'Demo', slug: 'demo', role: 'owner' }),
        {
          status: 201,
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);
    await createWorkspace('Demo', 'demo');
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/knowledge/workspaces'),
      expect.objectContaining({ method: 'POST' }),
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      name: 'Demo',
      slug: 'demo',
    });
  });

  it('labels operator provenance and searches only the selected workspace', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: 'k1' }), { status: 201 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ items: [], trust_notice: 'untrusted' }), {
          status: 200,
        }),
      );
    vi.stubGlobal('fetch', fetchMock);
    await createKnowledge('w1', {
      category: 'policy',
      title: 'Policy',
      content: 'Approved facts',
      sensitivity: 'internal',
    });
    await searchKnowledge('w1', 'sponsor rules');
    expect(fetchMock.mock.calls[0][0]).toContain('/workspaces/w1/items');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).provenance).toEqual({
      entered_by: 'authenticated_operator',
    });
    expect(fetchMock.mock.calls[1][0]).toContain('/workspaces/w1/search');
  });
});
