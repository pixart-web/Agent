'use client';

import type { MarketingCampaign, MarketingContent } from '@agent/shared';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  listMarketingCampaigns,
  listMarketingContentCalendar,
} from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function MarketingPage() {
  const { user, loading } = useAuthenticatedUser();
  const [query, setQuery] = useState('');
  const [campaigns, setCampaigns] = useState<MarketingCampaign[]>([]);
  const [scheduled, setScheduled] = useState<MarketingContent[]>([]);
  const [error, setError] = useState('');

  function refresh(search = '') {
    setError('');
    const startsAt = new Date();
    const endsAt = new Date(startsAt);
    endsAt.setDate(endsAt.getDate() + 30);

    return Promise.all([
      listMarketingCampaigns(search),
      listMarketingContentCalendar(
        startsAt.toISOString(),
        endsAt.toISOString(),
      ),
    ])
      .then(([campaignValue, calendarValue]) => {
        setCampaigns(campaignValue.campaigns);
        setScheduled(calendarValue.content);
      })
      .catch(() => setError('Unable to load campaigns.'));
  }

  useEffect(() => {
    if (user) void refresh();
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">Loading marketing operations…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Governed content operations</p>
          <h1>Marketing</h1>
          <p>
            Campaigns and drafts are untrusted business data. Kiko never
            publishes externally from this workspace.
          </p>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void refresh(query.trim());
          }}
        >
          <label>
            Search campaigns
            <input
              value={query}
              maxLength={255}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <button className="secondary-button" type="submit">
            Search
          </button>
        </form>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <section className="workflow-panel">
        <h2>Campaigns</h2>
        <div className="agent-grid">
          {campaigns.map((campaign) => (
            <Link
              className="agent-card agent-card--link"
              href={'/dashboard/marketing/campaigns/' + campaign.id}
              key={campaign.id}
            >
              <p className="eyebrow">{campaign.status}</p>
              <h3>{campaign.name}</h3>
              <p>{campaign.objective}</p>
            </Link>
          ))}
        </div>
        {campaigns.length === 0 && (
          <p className="empty-state">No campaigns found.</p>
        )}
      </section>
      <section className="workflow-panel">
        <h2>Next 30 days</h2>
        <p>
          Approved content scheduled in the editorial calendar. Scheduling does
          not publish content externally.
        </p>
        <div className="agent-grid">
          {scheduled.map((content) => (
            <Link
              className="agent-card agent-card--link"
              href={'/dashboard/marketing/content/' + content.id}
              key={content.id}
            >
              <p className="eyebrow">
                {content.channel} · {content.lifecycle_status}
              </p>
              <h3>{content.title}</h3>
              <p>
                {content.scheduled_for
                  ? new Date(content.scheduled_for).toLocaleString()
                  : 'Schedule pending'}
              </p>
            </Link>
          ))}
        </div>
        {scheduled.length === 0 && (
          <p className="empty-state">No content scheduled in this window.</p>
        )}
      </section>{' '}
    </main>
  );
}
