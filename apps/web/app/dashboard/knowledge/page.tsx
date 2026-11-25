'use client';

import type { KnowledgeItem, Workspace } from '@agent/shared';
import { FormEvent, useCallback, useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  approveKnowledge,
  archiveKnowledge,
  createKnowledge,
  createWorkspace,
  ingestKnowledgeDocument,
  listKnowledge,
  listWorkspaces,
  searchKnowledge,
} from '../../../lib/knowledge-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import { label } from '../../../lib/labels';
import { failureMessage } from '../../../lib/api-messages';

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
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentCategory, setDocumentCategory] =
    useState<KnowledgeItem['category']>('approved_knowledge');
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
        setError('Não foi possível carregar o conhecimento do negócio.'),
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
    } catch (failure) {
      setError(failureMessage(failure, 'Não foi possível criar o workspace.'));
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
        'Rascunho guardado. Um dono ou administrador tem de o aprovar antes de poder ser usado.',
      );
      await refresh();
    } catch (failure) {
      setError(
        failureMessage(
          failure,
          'Não foi possível guardar o rascunho de conhecimento.',
        ),
      );
    }
  }

  async function runSearch(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    try {
      const result = await searchKnowledge(selected, query.trim());
      setItems(result.items);
      setNotice(result.trust_notice);
    } catch (failure) {
      setError(failureMessage(failure, 'A pesquisa de conhecimento falhou.'));
    }
  }

  const selectedWorkspace = workspaces.find((space) => space.id === selected);

  if (loading || !user)
    return <main className="loading-page">A carregar o conhecimento…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Memória do workspace</p>
          <h1>Conhecimento do negócio</h1>
          <p>
            Dados de referência aprovados, com origem registada e limitados ao
            workspace.
          </p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {notice && <p className="workflow-success">{notice}</p>}
      <section className="workflow-panel">
        <h2>Workspace</h2>
        <select
          aria-label="Workspace"
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
        >
          <option value="">Escolhe um workspace</option>
          {workspaces.map((space) => (
            <option key={space.id} value={space.id}>
              {space.name} · {label(space.role)}
            </option>
          ))}
        </select>
        <form className="workflow-form" onSubmit={createSpace}>
          <label>
            Nome
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
          <button type="submit">Criar workspace</button>
        </form>
      </section>
      {selected && (
        <>
          {selectedWorkspace?.role !== 'viewer' && (
            <>
              <section className="workflow-panel">
                <h2>Adicionar rascunho de conhecimento</h2>
                <form className="workflow-form" onSubmit={createItem}>
                  <label>
                    Título
                    <input
                      required
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                    />
                  </label>
                  <label>
                    Conteúdo
                    <textarea
                      required
                      value={content}
                      onChange={(event) => setContent(event.target.value)}
                    />
                  </label>
                  <button type="submit">Guardar rascunho</button>
                </form>
              </section>
              <section className="workflow-panel">
                <h2>Importar um documento</h2>
                <p>
                  TXT, Markdown, PDF, or DOCX up to 5 MB. Only extracted text
                  and provenance are retained; every document starts as an
                  unapproved draft.
                </p>
                <form
                  className="workflow-form"
                  onSubmit={async (event) => {
                    event.preventDefault();
                    if (!documentFile) return;
                    try {
                      await ingestKnowledgeDocument(
                        selected,
                        documentFile,
                        documentCategory,
                        'internal',
                      );
                      setDocumentFile(null);
                      setNotice(
                        'Document extracted safely and saved as a draft.',
                      );
                      await refresh();
                    } catch (failure) {
                      setError(
                        failureMessage(
                          failure,
                          'Não foi possível importar o documento com segurança.',
                        ),
                      );
                    }
                  }}
                >
                  <label>
                    Categoria
                    <select
                      value={documentCategory}
                      onChange={(event) =>
                        setDocumentCategory(
                          event.target.value as KnowledgeItem['category'],
                        )
                      }
                    >
                      <option value="approved_knowledge">
                        Conhecimento geral
                      </option>
                      <option value="company_profile">Perfil da empresa</option>
                      <option value="service">Serviço</option>
                      <option value="product">Produto</option>
                      <option value="policy">Política</option>
                      <option value="brand_guideline">Diretriz de marca</option>
                      <option value="procedure">Procedimento</option>
                    </select>
                  </label>
                  <label>
                    Documento
                    <input
                      required
                      type="file"
                      accept=".txt,.md,.pdf,.docx,text/plain,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                      onChange={(event) =>
                        setDocumentFile(event.target.files?.[0] ?? null)
                      }
                    />
                  </label>
                  <button disabled={!documentFile}>Extrair documento</button>
                </form>
              </section>
            </>
          )}
          <section className="workflow-panel">
            <h2>Pesquisar conhecimento aprovado</h2>
            <form className="workflow-form" onSubmit={runSearch}>
              <label>
                Pergunta
                <input
                  required
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </label>
              <button type="submit">Pesquisar</button>
            </form>
            <div className="activity-list">
              {items.map((entry) => (
                <article className="activity-item" key={entry.id}>
                  <p className="eyebrow">
                    {label(entry.category)} · {label(entry.status)} ·{' '}
                    {label(entry.sensitivity)}
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
                        Aprovar
                      </button>
                    )}
                  {(selectedWorkspace?.role === 'owner' ||
                    selectedWorkspace?.role === 'admin') && (
                    <button
                      className="text-button"
                      type="button"
                      onClick={() =>
                        void archiveKnowledge(selected, entry.id).then(refresh)
                      }
                    >
                      Arquivar
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
