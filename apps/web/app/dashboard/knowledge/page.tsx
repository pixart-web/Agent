'use client';

import type { KnowledgeItem, Workspace } from '@agent/shared';
import { FormEvent, useCallback, useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  approveKnowledge,
  createKnowledge,
  createWorkspace,
  listKnowledge,
  listWorkspaces,
  searchKnowledge,
} from '../../../lib/knowledge-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function KnowledgePage() {
  const { user, loading } = useAuthenticatedUser();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selected, setSelected] = useState('');
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [query, setQuery] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    const spaces = await listWorkspaces();
    setWorkspaces(spaces);
    const workspaceId = selected || spaces[0]?.id || '';
    if (!selected && workspaceId) setSelected(workspaceId);
    setItems(workspaceId ? await listKnowledge(workspaceId) : []);
  }, [selected]);

  useEffect(() => {
    if (user)
      void refresh().catch(() =>
        setError('Unable to load business knowledge.'),
      );
  }, [refresh, user]);

  async function createSpace(event: FormEvent) {
    event.preventDefault();
    try {
      const value = await createWorkspace(name.trim(), slug.trim());
      setSelected(value.id);
      setName('');
      setSlug('');
      setNotice('Workspace created with you as owner.');
    } catch {
      setError('Workspace could not be created.');
    }
  }

  async function createItem(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    try {
      await createKnowledge(selected, {
        category: 'approved_knowledge',
        title: title.trim(),
        content: content.trim(),
        sensitivity: 'internal',
      });
      setTitle('');
      setContent('');
      setNotice(
        'Draft saved. An owner or admin must approve it before retrieval.',
      );
      await refresh();
    } catch {
      setError('Knowledge draft could not be saved.');
    }
  }

  async function runSearch(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    try {
      const result = await searchKnowledge(selected, query.trim());
      setItems(result.items);
      setNotice(result.trust_notice);
    } catch {
      setError('Knowledge search failed.');
    }
  }

  const selectedWorkspace = workspaces.find((space) => space.id === selected);

  if (loading || !user)
    return <main className="loading-page">Loading knowledge…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Workspace memory</p>
          <h1>Business knowledge</h1>
          <p>
            Approved, provenance-aware reference data with strict workspace
            boundaries.
          </p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {notice && <p className="workflow-success">{notice}</p>}
      <section className="workflow-panel">
        <h2>Workspace</h2>
        <select
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
        >
          <option value="">Select a workspace</option>
          {workspaces.map((space) => (
            <option key={space.id} value={space.id}>
              {space.name} · {space.role}
            </option>
          ))}
        </select>
        <form className="workflow-form" onSubmit={createSpace}>
          <label>
            Name
            <input
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label>
            Slug
            <input
              required
              pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
              value={slug}
              onChange={(event) => setSlug(event.target.value)}
            />
          </label>
          <button type="submit">Create workspace</button>
        </form>
      </section>
      {selected && (
        <>
          <section className="workflow-panel">
            <h2>Add a knowledge draft</h2>
            <form className="workflow-form" onSubmit={createItem}>
              <label>
                Title
                <input
                  required
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                />
              </label>
              <label>
                Content
                <textarea
                  required
                  value={content}
                  onChange={(event) => setContent(event.target.value)}
                />
              </label>
              <button type="submit">Save draft</button>
            </form>
          </section>
          <section className="workflow-panel">
            <h2>Search approved knowledge</h2>
            <form className="workflow-form" onSubmit={runSearch}>
              <label>
                Question
                <input
                  required
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>
              <button type="submit">Search</button>
            </form>
            <div className="activity-list">
              {items.map((entry) => (
                <article className="activity-item" key={entry.id}>
                  <p className="eyebrow">
                    {entry.category} · {entry.status} · {entry.sensitivity}
                  </p>
                  <h3>{entry.title}</h3>
                  <p>{entry.content}</p>
                  <p>
                    Source: {entry.source_type}
                    {entry.source_reference
                      ? ` · ${entry.source_reference}`
                      : ''}
                  </p>
                  {entry.status === 'draft' &&
                    (selectedWorkspace?.role === 'owner' ||
                      selectedWorkspace?.role === 'admin') && (
                      <button
                        type="button"
                        onClick={() =>
                          void approveKnowledge(selected, entry.id).then(
                            refresh,
                          )
                        }
                      >
                        Approve
                      </button>
                    )}
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
