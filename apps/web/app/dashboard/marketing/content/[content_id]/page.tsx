'use client';

import type { MarketingContentDetail } from '@agent/shared';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../../components/dashboard-nav';
import { getMarketingContent } from '../../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../../lib/use-authenticated-user';

export default function MarketingContentPage() {
  const { user, loading } = useAuthenticatedUser();
  const { content_id: contentId } = useParams<{ content_id: string }>();
  const [detail, setDetail] = useState<MarketingContentDetail | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    void getMarketingContent(contentId)
      .then(setDetail)
      .catch(() => setError('Unable to load this content item.'));
  }, [contentId, user]);

  if (loading || !user)
    return <main className="loading-page">Loading content…</main>;

  const content = detail?.content;
  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">
            Content · {content?.lifecycle_status || 'loading'}
          </p>
          <h1>{content?.title || 'Content item'}</h1>
          <p>
            {content?.content_type} · {content?.channel}
          </p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {detail && (
        <>
          <section className="workflow-panel">
            <h2>Draft copy</h2>
            <p className="eyebrow">Untrusted draft · never auto-published</p>
            <p>{detail.content.body}</p>
          </section>
          <section className="workflow-panel">
            <h2>Lifecycle history</h2>
            {detail.history.map((item) => (
              <p key={item.id}>
                {item.from_status || 'created'} → {item.to_status} ·{' '}
                {item.reason || 'No reason supplied'}
              </p>
            ))}
          </section>
          <section className="workflow-panel">
            <h2>Asset metadata</h2>
            {detail.assets.map((asset) => (
              <article className="agent-card" key={asset.id}>
                <p className="eyebrow">{asset.media_type}</p>
                <h3>{asset.name}</h3>
                <p>{asset.locator}</p>
              </article>
            ))}
            {detail.assets.length === 0 && (
              <p className="empty-state">No asset metadata.</p>
            )}
          </section>
          <section className="workflow-panel">
            <h2>Confirmed publications</h2>
            {detail.publications.map((publication) => (
              <article className="agent-card" key={publication.id}>
                <p className="eyebrow">
                  Externally confirmed · {publication.channel}
                </p>
                <p>{publication.external_reference}</p>
                <p>{new Date(publication.published_at).toLocaleString()}</p>
              </article>
            ))}
            {detail.publications.length === 0 && (
              <p className="empty-state">Nothing recorded as published.</p>
            )}
          </section>
          <section className="workflow-panel">
            <h2>Performance metadata</h2>
            {detail.metrics.map((metric) => (
              <p key={metric.id}>
                {metric.metric_name}: {metric.value} · {metric.source}
              </p>
            ))}
            {detail.metrics.length === 0 && (
              <p className="empty-state">No performance metadata.</p>
            )}
          </section>
        </>
      )}
    </main>
  );
}
