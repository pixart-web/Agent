'use client';

import type { MarketingCampaign, MarketingContent } from '@agent/shared';
import Link from 'next/link';
import { useParams } from '../../../../../lib/route-params';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../../components/dashboard-nav';
import {
  createMarketingContent,
  getMarketingCampaign,
  listMarketingContent,
  updateMarketingCampaign,
} from '../../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../../lib/use-authenticated-user';
import { CanEdit } from '../../../../../lib/workspace-access';
import { failureMessage } from '../../../../../lib/api-messages';

export default function MarketingCampaignPage() {
  const { user, loading } = useAuthenticatedUser();
  const { campaign_id: campaignId } = useParams<{ campaign_id: string }>();
  const [campaign, setCampaign] = useState<MarketingCampaign | null>(null);
  const [content, setContent] = useState<MarketingContent[]>([]);
  const [error, setError] = useState('');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [channel, setChannel] = useState('linkedin');

  useEffect(() => {
    if (!user) return;
    void Promise.all([
      getMarketingCampaign(campaignId),
      listMarketingContent(campaignId),
    ])
      .then(([campaignValue, contentValue]) => {
        setCampaign(campaignValue);
        setContent(contentValue.content);
      })
      .catch(() => setError('Não foi possível carregar esta campanha.'));
  }, [campaignId, user]);

  if (loading || !user)
    return <main className="loading-page">A carregar a campanha…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Campaign · {campaign?.status || 'loading'}</p>
          <h1>{campaign?.name || 'Campanha'}</h1>
          <p>{campaign?.objective}</p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {campaign && (
        <section className="workflow-panel">
          <label>
            Ciclo de vida da campanha
            <select
              value={campaign.status}
              onChange={async (event) => {
                try {
                  setCampaign(
                    await updateMarketingCampaign(campaign.id, {
                      status: event.target.value,
                    }),
                  );
                } catch (failure) {
                  setError(
                    failureMessage(
                      failure,
                      'Não foi possível atualizar esta campanha.',
                    ),
                  );
                }
              }}
            >
              <option value="idea">Ideia</option>
              <option value="active">Ativo</option>
              <option value="paused">Em pausa</option>
              <option value="completed">Concluído</option>
              <option value="archived">Arquivado</option>
            </select>
          </label>
        </section>
      )}
      <CanEdit>
        <section className="workflow-panel">
          <h2>Criar rascunho de conteúdo</h2>
          <form
            className="workflow-form"
            onSubmit={async (event) => {
              event.preventDefault();
              try {
                await createMarketingContent({
                  campaign_id: campaignId,
                  content_type: 'social_post',
                  channel,
                  title,
                  body,
                });
                setTitle('');
                setBody('');
                setContent((await listMarketingContent(campaignId)).content);
              } catch (failure) {
                setError(
                  failureMessage(
                    failure,
                    'Não foi possível criar este rascunho.',
                  ),
                );
              }
            }}
          >
            <label>
              Canal
              <input
                required
                value={channel}
                onChange={(event) => setChannel(event.target.value)}
              />
            </label>
            <label>
              Título
              <input
                required
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
            </label>
            <label>
              Texto do rascunho
              <textarea
                required
                value={body}
                onChange={(event) => setBody(event.target.value)}
              />
            </label>
            <button>Criar rascunho</button>
          </form>
        </section>
      </CanEdit>
      <section className="workflow-panel">
        <h2>Ciclo de vida do conteúdo</h2>
        <div className="agent-grid">
          {content.map((item) => (
            <Link
              className="agent-card agent-card--link"
              href={'/dashboard/marketing/content/' + item.id}
              key={item.id}
            >
              <p className="eyebrow">
                {item.lifecycle_status} · {item.channel}
              </p>
              <h3>{item.title}</h3>
              <p>{item.content_type}</p>
              <p>
                Scheduled:{' '}
                {item.scheduled_for
                  ? new Date(item.scheduled_for).toLocaleString('pt-PT')
                  : 'Não agendado'}
              </p>
            </Link>
          ))}
        </div>
        {content.length === 0 && <p className="empty-state">Sem conteúdos.</p>}
      </section>
    </main>
  );
}
