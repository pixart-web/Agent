'use client';

import type {
  CalendarIntegrationStatus,
  EmailIntegrationStatus,
  GitHubIntegrationStatus,
} from '@agent/shared';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  getCalendarIntegrationStatus,
  getEmailIntegrationStatus,
  getGitHubIntegrationStatus,
} from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function IntegrationsPage() {
  const { user, loading } = useAuthenticatedUser();
  const [github, setGitHub] = useState<GitHubIntegrationStatus | null>(null);
  const [email, setEmail] = useState<EmailIntegrationStatus | null>(null);
  const [calendar, setCalendar] = useState<CalendarIntegrationStatus | null>(
    null,
  );

  useEffect(() => {
    if (user) {
      void getGitHubIntegrationStatus().then(setGitHub);
      void getEmailIntegrationStatus().then(setEmail);
      void getCalendarIntegrationStatus().then(setCalendar);
    }
  }, [user]);

  if (loading || !user) {
    return <main className="loading-page">A carregar as integrações…</main>;
  }

  const connected = Boolean(github?.enabled && github?.credential_configured);

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Serviços externos</p>
          <h1>Integrações</h1>
          <p>As credenciais ficam no servidor e nunca são mostradas aqui.</p>
        </div>
      </section>
      <div className="agent-grid">
        <Link
          className="agent-card agent-card--link"
          href="/dashboard/integrations/github"
        >
          <p className="eyebrow">Ferramentas de desenvolvimento</p>
          <h2>GitHub</h2>
          <p>Estado: {connected ? 'Ligado' : 'Não configurado'}</p>
          <p>
            Repositórios permitidos:{' '}
            {github?.allowed_repositories.join(', ') || 'Nenhum'}
          </p>
        </Link>
        <Link
          className="agent-card agent-card--link"
          href="/dashboard/integrations/email"
        >
          <p className="eyebrow">Comunicação</p>
          <h2>Email</h2>
          <p>Estado: {email?.connected_accounts ? 'Ligado' : 'Não ligado'}</p>
          <p>Provider: {email?.provider || 'gmail'}</p>
        </Link>
        <Link
          className="agent-card agent-card--link"
          href="/dashboard/integrations/calendar"
        >
          <p className="eyebrow">Agendamento</p>
          <h2>Calendário</h2>
          <p>
            Estado: {calendar?.connected_accounts ? 'Ligado' : 'Não ligado'}
          </p>
          <p>Provider: {calendar?.provider || 'google_calendar'}</p>
        </Link>{' '}
      </div>
    </main>
  );
}
