'use client';

import type { MarketingCampaign, MarketingContent } from '@agent/shared';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  createMarketingCampaign,
  listMarketingCampaigns,
  listMarketingContentCalendar,
} from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import { CanEdit } from '../../../lib/workspace-access';
import { label } from '../../../lib/labels';

export default function MarketingPage() {
  const { user, loading } = useAuthenticatedUser();
  const [query, setQuery] = useState('');
  const [campaigns, setCampaigns] = useState<MarketingCampaign[]>([]);
  const [scheduled, setScheduled] = useState<MarketingContent[]>([]);
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [objective, setObjective] = useState('');
  const [saving, setSaving] = useState(false);

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
      .catch(() => setError('Não foi possível carregar as campanhas.'));
  }

  useEffect(() => {
    if (user) void refresh();
  }, [user]);

  if (loading || !user)
    return (
      <main className="loading-page">
        A carregar as operações de marketing…
      </main>
    );

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Operações de conteúdo governadas</p>
          <h1>Marketing</h1>
          <p>
            Campanhas e rascunhos são dados de negócio não verificados. O Kiko
            nunca publica externamente a partir deste workspace.
          </p>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void refresh(query.trim());
          }}
        >
          <label>
            Pesquisar campanhas
            <input
              value={query}
              maxLength={255}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <button className="secondary-button" type="submit">
            Pesquisar
          </button>
        </form>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <CanEdit>
        <section className="workflow-panel">
          <h2>Criar campanha</h2>
          <form
            className="workflow-form"
            onSubmit={async (event) => {
              event.preventDefault();
              setSaving(true);
              setError('');
              try {
                await createMarketingCampaign({ name, objective });
                setName('');
                setObjective('');
                await refresh(query.trim());
              } catch {
                setError('Não foi possível criar esta campanha.');
              } finally {
                setSaving(false);
              }
            }}
          >
            <label>
              Nome da campanha
              <input
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label>
              Objetivo
              <textarea
                required
                value={objective}
                onChange={(event) => setObjective(event.target.value)}
              />
            </label>
            <button disabled={saving}>Criar campanha</button>
          </form>
        </section>
      </CanEdit>
      <section className="workflow-panel">
        <h2>Campanhas</h2>
        <div className="agent-grid">
          {campaigns.map((campaign) => (
            <Link
              className="agent-card agent-card--link"
              href={'/dashboard/marketing/campaigns/' + campaign.id}
              key={campaign.id}
            >
              <p className="eyebrow">{label(campaign.status)}</p>
              <h3>{campaign.name}</h3>
              <p>{campaign.objective}</p>
            </Link>
          ))}
        </div>
        {campaigns.length === 0 && (
          <p className="empty-state">Nenhuma campanha encontrada.</p>
        )}
      </section>
      <section className="workflow-panel">
        <h2>Próximos 30 dias</h2>
        <p>
          Conteúdo aprovado e agendado no calendário editorial. Agendar não
          publica nada externamente.
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
                  ? new Date(content.scheduled_for).toLocaleString('pt-PT')
                  : 'Agendamento pendente'}
              </p>
            </Link>
          ))}
        </div>
        {scheduled.length === 0 && (
          <p className="empty-state">Nenhum conteúdo agendado neste período.</p>
        )}
      </section>{' '}
    </main>
  );
}
