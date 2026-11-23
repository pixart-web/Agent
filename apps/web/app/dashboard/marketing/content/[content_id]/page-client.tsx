'use client';

import type { MarketingContentDetail } from '@agent/shared';
import { useParams } from '../../../../../lib/route-params';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../../components/dashboard-nav';
import {
  getMarketingContent,
  scheduleMarketingContent,
  transitionMarketingContent,
} from '../../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../../lib/use-authenticated-user';
import { CanEdit } from '../../../../../lib/workspace-access';

export default function MarketingContentPage() {
  const { user, loading } = useAuthenticatedUser();
  const { content_id: contentId } = useParams<{ content_id: string }>();
  const [detail, setDetail] = useState<MarketingContentDetail | null>(null);
  const [error, setError] = useState('');
  const [scheduledFor, setScheduledFor] = useState('');

  async function transition(
    target: 'draft' | 'review' | 'approved' | 'archived',
  ) {
    try {
      await transitionMarketingContent(
        contentId,
        target,
        'Atualização do ciclo de vida pelo operador',
      );
      setDetail(await getMarketingContent(contentId));
    } catch {
      setError('Esta mudança de estado não é permitida.');
    }
  }

  useEffect(() => {
    if (!user) return;
    void getMarketingContent(contentId)
      .then(setDetail)
      .catch(() => setError('Não foi possível carregar este conteúdo.'));
  }, [contentId, user]);

  if (loading || !user)
    return <main className="loading-page">A carregar o conteúdo…</main>;

  const content = detail?.content;
  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">
            Content · {content?.lifecycle_status || 'loading'}
          </p>
          <h1>{content?.title || 'Conteúdo'}</h1>
          <p>
            {content?.content_type} · {content?.channel}
          </p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {detail && (
        <>
          <section className="workflow-panel">
            <h2>Texto do rascunho</h2>
            <p className="eyebrow">
              Rascunho não verificado · nunca publicado automaticamente
            </p>
            <p>{detail.content.body}</p>
            <CanEdit>
              <div className="button-row">
                {['idea', 'review', 'approved'].includes(
                  detail.content.lifecycle_status,
                ) && (
                  <button
                    className="secondary-button"
                    onClick={() => void transition('draft')}
                  >
                    Voltar a rascunho
                  </button>
                )}
                {detail.content.lifecycle_status === 'draft' && (
                  <button onClick={() => void transition('review')}>
                    Enviar para revisão
                  </button>
                )}
                {detail.content.lifecycle_status === 'review' && (
                  <button onClick={() => void transition('approved')}>
                    Aprovar conteúdo
                  </button>
                )}
                {detail.content.lifecycle_status !== 'archived' && (
                  <button
                    className="text-button"
                    onClick={() => void transition('archived')}
                  >
                    Arquivar
                  </button>
                )}
              </div>
            </CanEdit>
            <CanEdit>
              {detail.content.lifecycle_status === 'approved' && (
                <form
                  className="workflow-form"
                  onSubmit={async (event) => {
                    event.preventDefault();
                    try {
                      await scheduleMarketingContent(
                        contentId,
                        new Date(scheduledFor).toISOString(),
                      );
                      setDetail(await getMarketingContent(contentId));
                    } catch {
                      setError(
                        'Não foi possível agendar este conteúdo aprovado.',
                      );
                    }
                  }}
                >
                  <label>
                    Agendar para
                    <input
                      required
                      type="datetime-local"
                      value={scheduledFor}
                      onChange={(event) => setScheduledFor(event.target.value)}
                    />
                  </label>
                  <button>Agendamento</button>
                </form>
              )}
            </CanEdit>
          </section>
          <section className="workflow-panel">
            <h2>Histórico do ciclo de vida</h2>
            {detail.history.map((item) => (
              <p key={item.id}>
                {item.from_status || 'created'} → {item.to_status} ·{' '}
                {item.reason || 'Sem motivo indicado'}
              </p>
            ))}
          </section>
          <section className="workflow-panel">
            <h2>Metadados de recursos</h2>
            {detail.assets.map((asset) => (
              <article className="agent-card" key={asset.id}>
                <p className="eyebrow">{asset.media_type}</p>
                <h3>{asset.name}</h3>
                <p>{asset.locator}</p>
              </article>
            ))}
            {detail.assets.length === 0 && (
              <p className="empty-state">Sem metadados de recursos.</p>
            )}
          </section>
          <section className="workflow-panel">
            <h2>Publicações confirmadas</h2>
            {detail.publications.map((publication) => (
              <article className="agent-card" key={publication.id}>
                <p className="eyebrow">
                  Externally confirmed · {publication.channel}
                </p>
                <p>{publication.external_reference}</p>
                <p>
                  {new Date(publication.published_at).toLocaleString('pt-PT')}
                </p>
              </article>
            ))}
            {detail.publications.length === 0 && (
              <p className="empty-state">Nothing recorded as published.</p>
            )}
          </section>
          <section className="workflow-panel">
            <h2>Dados de desempenho</h2>
            {detail.metrics.map((metric) => (
              <p key={metric.id}>
                {metric.metric_name}: {metric.value} · {metric.source}
              </p>
            ))}
            {detail.metrics.length === 0 && (
              <p className="empty-state">Sem dados de desempenho.</p>
            )}
          </section>
        </>
      )}
    </main>
  );
}
