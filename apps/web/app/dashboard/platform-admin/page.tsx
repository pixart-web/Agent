'use client';

import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import { PixartAppsAdmin } from '../../../components/pixart-apps-admin';
import {
  getPlatformOverview,
  listPlatformUsers,
  listPlatformWorkspaces,
  setPlatformUserStatus,
  setPlatformWorkspaceStatus,
  type PlatformOverview,
  type PlatformUser,
  type PlatformWorkspace,
} from '../../../lib/platform-admin-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import { label } from '../../../lib/labels';

export default function PlatformAdminPage() {
  const { user, loading } = useAuthenticatedUser();
  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [workspaces, setWorkspaces] = useState<PlatformWorkspace[]>([]);
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [error, setError] = useState('');

  async function refresh() {
    const [nextOverview, nextWorkspaces, nextUsers] = await Promise.all([
      getPlatformOverview(),
      listPlatformWorkspaces(),
      listPlatformUsers(),
    ]);
    setOverview(nextOverview);
    setWorkspaces(nextWorkspaces);
    setUsers(nextUsers);
  }

  useEffect(() => {
    if (user?.is_superuser)
      void refresh().catch(() =>
        setError('Não foi possível carregar os dados da plataforma.'),
      );
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">A carregar a administração…</main>;
  if (!user.is_superuser)
    return (
      <main>
        <DashboardNav user={user} />
        <section className="workflow-panel">
          <h1>Administração da plataforma</h1>
          <p>
            Esta área exige acesso de administrador da plataforma, concedido à
            parte.
          </p>
        </section>
      </main>
    );

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Área de controlo restrita</p>
          <h1>Administração da plataforma</h1>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {overview && (
        <section className="agent-grid">
          {[
            ['Workspaces', overview.workspace_count],
            ['Workspaces ativos', overview.active_workspace_count],
            ['Utilizadores', overview.user_count],
            ['Utilizadores ativos', overview.active_user_count],
            ['Sessões ativas', overview.active_session_count],
            ['Integrações', overview.integration_account_count],
            ['Email falhado', overview.failed_email_count],
          ].map(([label, value]) => (
            <article className="agent-card" key={label}>
              <p className="eyebrow">{label}</p>
              <h2>{value}</h2>
            </article>
          ))}
        </section>
      )}
      <section className="workflow-panel">
        <div className="workflow-panel__heading">
          <h2>Diagnóstico do fornecedor</h2>
        </div>
        <div className="activity-list">
          {overview?.providers.map((provider) => (
            <article className="activity-item" key={provider.provider}>
              <strong>{provider.provider}</strong>
              <p>
                Enabled: {provider.enabled ? 'yes' : 'no'} · Configured:{' '}
                {provider.configured ? 'yes' : 'no'}
              </p>
            </article>
          ))}
        </div>
        <p>Subscriptions: {overview?.subscription_status.replace('_', ' ')}</p>
      </section>
      <section className="workflow-panel">
        <div className="workflow-panel__heading">
          <h2>Workspaces</h2>
        </div>
        <div className="activity-list">
          {workspaces.map((workspace) => (
            <article className="activity-item" key={workspace.id}>
              <strong>{workspace.name}</strong>
              <p>
                {workspace.slug} · {workspace.member_count} membros ·{' '}
                {label(workspace.status)}
              </p>
              <button
                className="secondary-button"
                onClick={() =>
                  void setPlatformWorkspaceStatus(
                    workspace.id,
                    workspace.status === 'active' ? 'suspended' : 'active',
                  ).then(refresh)
                }
              >
                {workspace.status === 'active' ? 'Suspend' : 'Activate'}
              </button>
            </article>
          ))}
        </div>
      </section>
      <section className="workflow-panel">
        <div className="workflow-panel__heading">
          <h2>Utilizadores</h2>
        </div>
        <div className="activity-list">
          {users.map((item) => (
            <article className="activity-item" key={item.id}>
              <strong>{item.full_name}</strong>
              <p>
                {item.email} · {item.is_superuser ? 'platform admin' : 'user'} ·{' '}
                {item.is_active ? 'active' : 'inactive'}
              </p>
              {item.id !== user.id && (
                <button
                  className="secondary-button"
                  onClick={() =>
                    void setPlatformUserStatus(item.id, !item.is_active).then(
                      refresh,
                    )
                  }
                >
                  {item.is_active ? 'Desativar' : 'Ativar'}
                </button>
              )}
            </article>
          ))}
        </div>
      </section>
      <PixartAppsAdmin />
    </main>
  );
}
