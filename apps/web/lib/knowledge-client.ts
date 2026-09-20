import type { KnowledgeItem, Workspace } from '@agent/shared';

import { authFetch } from './auth-client';

async function json<T>(response: Response): Promise<T> {
  if (!response.ok)
    throw new Error(`Knowledge request failed (${response.status})`);
  return (await response.json()) as T;
}

export async function listWorkspaces(): Promise<Workspace[]> {
  const result = await json<{ workspaces: Workspace[] }>(
    await authFetch('/api/v1/knowledge/workspaces'),
  );
  return result.workspaces;
}

export async function createWorkspace(
  name: string,
  slug: string,
): Promise<Workspace> {
  return json<Workspace>(
    await authFetch('/api/v1/knowledge/workspaces', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, slug }),
    }),
  );
}

export async function listKnowledge(
  workspaceId: string,
): Promise<KnowledgeItem[]> {
  const result = await json<{ items: KnowledgeItem[] }>(
    await authFetch(
      `/api/v1/knowledge/workspaces/${workspaceId}/items?include_drafts=true`,
    ),
  );
  return result.items;
}

export async function createKnowledge(
  workspaceId: string,
  value: Pick<KnowledgeItem, 'category' | 'title' | 'content' | 'sensitivity'>,
): Promise<KnowledgeItem> {
  return json<KnowledgeItem>(
    await authFetch(`/api/v1/knowledge/workspaces/${workspaceId}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...value,
        source_type: 'operator',
        provenance: { entered_by: 'authenticated_operator' },
      }),
    }),
  );
}

export async function approveKnowledge(
  workspaceId: string,
  itemId: string,
): Promise<KnowledgeItem> {
  return json<KnowledgeItem>(
    await authFetch(
      `/api/v1/knowledge/workspaces/${workspaceId}/items/${itemId}/approve`,
      {
        method: 'POST',
      },
    ),
  );
}

export async function searchKnowledge(
  workspaceId: string,
  query: string,
): Promise<{ items: KnowledgeItem[]; trust_notice: string }> {
  return json(
    await authFetch(`/api/v1/knowledge/workspaces/${workspaceId}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    }),
  );
}
