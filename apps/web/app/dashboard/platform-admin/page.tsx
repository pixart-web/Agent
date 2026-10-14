'use client';

import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
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
      void refresh().catch(() => setError('Unable to load platform data.'));
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">Loading administration…</main>;
  if (!user.is_superuser)
    return (
      <main>
        <DashboardNav user={user} />
        <section className="workflow-panel">
          <h1>Platform administration</h1>
          <p>
            This area requires separately granted platform administrator access.
          </p>
        </section>
      </main>
    );

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Restricted control plane</p>
          <h1>Platform administration</h1>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {overview && (
        <section className="agent-grid">
          {[
            ['Workspaces', overview.workspace_count],
            ['Active workspaces', overview.active_workspace_count],
            ['Users', overview.user_count],
            ['Active users', overview.active_user_count],
            ['Active sessions', overview.active_session_count],
            ['Integrations', overview.integration_account_count],
            ['Failed email', overview.failed_email_count],
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
          <h2>Provider diagnostics</h2>
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
          <h2>Tenants</h2>
        </div>
        <div className="activity-list">
          {workspaces.map((workspace) => (
            <article className="activity-item" key={workspace.id}>
              <strong>{workspace.name}</strong>
              <p>
                {workspace.slug} · {workspace.member_count} members ·{' '}
                {workspace.status}
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
          <h2>Users</h2>
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
                  {item.is_active ? 'Deactivate' : 'Activate'}
                </button>
              )}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
