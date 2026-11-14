'use client';

import type { MarketingCampaign, MarketingContent } from '@agent/shared';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../../../components/dashboard-nav';
import {
  createMarketingContent,
  getMarketingCampaign,
  listMarketingContent,
  updateMarketingCampaign,
} from '../../../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../../../lib/use-authenticated-user';

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
      .catch(() => setError('Unable to load this campaign.'));
  }, [campaignId, user]);

  if (loading || !user)
    return <main className="loading-page">Loading campaign…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Campaign · {campaign?.status || 'loading'}</p>
          <h1>{campaign?.name || 'Campaign'}</h1>
          <p>{campaign?.objective}</p>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {campaign && (
        <section className="workflow-panel">
          <label>
            Campaign lifecycle
            <select
              value={campaign.status}
              onChange={async (event) => {
                try {
                  setCampaign(
                    await updateMarketingCampaign(campaign.id, {
                      status: event.target.value,
                    }),
                  );
                } catch {
                  setError('Unable to update this campaign.');
                }
              }}
            >
              <option value="idea">Idea</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
              <option value="archived">Archived</option>
            </select>
          </label>
        </section>
      )}
      <section className="workflow-panel">
        <h2>Create content draft</h2>
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
            } catch {
              setError('Unable to create this content draft.');
            }
          }}
        >
          <label>
            Channel
            <input
              required
              value={channel}
              onChange={(event) => setChannel(event.target.value)}
            />
          </label>
          <label>
            Title
            <input
              required
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <label>
            Draft copy
            <textarea
              required
              value={body}
              onChange={(event) => setBody(event.target.value)}
            />
          </label>
          <button>Create draft</button>
        </form>
      </section>
      <section className="workflow-panel">
        <h2>Content lifecycle</h2>
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
                  ? new Date(item.scheduled_for).toLocaleString()
                  : 'Not scheduled'}
              </p>
            </Link>
          ))}
        </div>
        {content.length === 0 && (
          <p className="empty-state">No content items.</p>
        )}
      </section>
    </main>
  );
}
