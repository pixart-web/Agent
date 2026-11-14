'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  AuthClientError,
  changePassword,
  listSessions,
  revokeSession,
  updateProfile,
} from '../../../lib/auth-client';
import type { Session } from '../../../lib/auth-types';
import {
  getNotificationPreferences,
  updateNotificationPreferences,
  type NotificationPreferences,
} from '../../../lib/notification-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import {
  downloadWorkspaceExport,
  getWorkspaceSettings,
  updateWorkspaceSettings,
  type WorkspaceSettings,
} from '../../../lib/workspace-settings-client';

export default function SettingsPage() {
  const router = useRouter();
  const { user, loading } = useAuthenticatedUser();
  const [fullName, setFullName] = useState('');
  const [language, setLanguage] = useState('en');
  const [timezone, setTimezone] = useState('UTC');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [message, setMessage] = useState('');
  const [notifications, setNotifications] =
    useState<NotificationPreferences | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceSettings | null>(null);

  useEffect(() => {
    if (!user) return;
    setFullName(user.full_name);
    setLanguage(user.language);
    setTimezone(user.timezone);
    void listSessions()
      .then(setSessions)
      .catch(() => setMessage('Unable to load sessions.'));
    void getNotificationPreferences()
      .then(setNotifications)
      .catch(() => setMessage('Unable to load notification preferences.'));
    void getWorkspaceSettings()
      .then(setWorkspace)
      .catch(() => setMessage('Unable to load workspace settings.'));
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">Loading settings…</main>;

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    try {
      await updateProfile(fullName.trim(), language, timezone);
      setMessage('Profile updated.');
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Unable to update profile.',
      );
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    try {
      await changePassword(currentPassword, newPassword);
      router.replace('/login');
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Unable to change password.',
      );
    }
  }

  async function removeSession(id: string) {
    await revokeSession(id);
    setSessions((items) => items.filter((item) => item.id !== id));
  }

  return (
    <main>
      <DashboardNav user={user} />
      <section className="hero compact-hero">
        <div>
          <p className="eyebrow">Account</p>
          <h1>Settings</h1>
          {workspace?.is_synthetic_demo ? (
            <p className="status-pill warning">
              Synthetic demo workspace — no real customer data or external
              delivery.
            </p>
          ) : null}
        </div>
      </section>
      <section className="workflow-grid">
        <form className="workflow-panel auth-form" onSubmit={saveProfile}>
          <div className="workflow-panel__heading">
            <h2>Profile</h2>
          </div>
          <label>
            Full name
            <input
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
            />
          </label>
          <label>
            Email
            <input value={user.email} disabled />
          </label>
          <label>
            Language
            <select
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
            >
              <option value="en">English</option>
              <option value="pt-PT">Português (Portugal)</option>
            </select>
          </label>
          <label>
            Timezone
            <input
              value={timezone}
              onChange={(event) => setTimezone(event.target.value)}
            />
          </label>
          <button className="primary-button" type="submit">
            Save profile
          </button>
        </form>
        <form className="workflow-panel auth-form" onSubmit={savePassword}>
          <div className="workflow-panel__heading">
            <h2>Change password</h2>
          </div>
          <label>
            Current password
            <input
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
            />
          </label>
          <label>
            New password
            <input
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
            />
          </label>
          <button className="primary-button" type="submit">
            Change password
          </button>
        </form>
      </section>
      {workspace && (
        <form
          className="workflow-panel auth-form"
          onSubmit={async (event) => {
            event.preventDefault();
            setWorkspace(await updateWorkspaceSettings(workspace));
            setMessage('Workspace settings updated.');
          }}
        >
          <div className="workflow-panel__heading">
            <h2>Workspace</h2>
          </div>
          <label>
            Name
            <input
              value={workspace.name}
              onChange={(event) =>
                setWorkspace({ ...workspace, name: event.target.value })
              }
            />
          </label>
          <label>
            Description
            <textarea
              value={workspace.description ?? ''}
              onChange={(event) =>
                setWorkspace({
                  ...workspace,
                  description: event.target.value || null,
                })
              }
            />
          </label>
          <label>
            Sector
            <input
              value={workspace.sector ?? ''}
              onChange={(event) =>
                setWorkspace({
                  ...workspace,
                  sector: event.target.value || null,
                })
              }
            />
          </label>
          <label>
            Country code
            <input
              maxLength={2}
              value={workspace.country ?? ''}
              onChange={(event) =>
                setWorkspace({
                  ...workspace,
                  country: event.target.value.toUpperCase() || null,
                })
              }
            />
          </label>
          <label>
            Website
            <input
              type="url"
              value={workspace.website ?? ''}
              onChange={(event) =>
                setWorkspace({
                  ...workspace,
                  website: event.target.value || null,
                })
              }
            />
          </label>
          <label>
            Data retention (days)
            <input
              type="number"
              min={30}
              max={3650}
              value={workspace.retention_days}
              onChange={(event) =>
                setWorkspace({
                  ...workspace,
                  retention_days: Number(event.target.value),
                })
              }
            />
          </label>
          <label>
            Monthly AI token limit
            <input
              type="number"
              min={1000}
              value={workspace.ai_monthly_token_limit ?? ''}
              onChange={(event) =>
                setWorkspace({
                  ...workspace,
                  ai_monthly_token_limit: event.target.value
                    ? Number(event.target.value)
                    : null,
                })
              }
            />
          </label>
          <button
            className="primary-button"
            disabled={!['owner', 'admin'].includes(workspace.role)}
          >
            Save workspace
          </button>
        </form>
      )}
      {workspace && (
        <section className="workflow-panel">
          <div className="workflow-panel__heading">
            <h2>Team and roles</h2>
          </div>
          <div className="activity-list">
            {workspace.members.map((member) => (
              <article className="activity-item" key={member.id}>
                <strong>{member.full_name}</strong>
                <p>
                  {member.email} · {member.role}
                </p>
              </article>
            ))}
          </div>
        </section>
      )}
      {workspace && ['owner', 'admin'].includes(workspace.role) && (
        <section className="workflow-panel">
          <div className="workflow-panel__heading">
            <div>
              <p className="eyebrow">Data portability</p>
              <h2>Workspace export</h2>
            </div>
          </div>
          <p className="empty-state">
            Download the workspace profile, CRM records, projects, tasks and
            activities. Authentication secrets and integration credentials are
            excluded. Every export is recorded in the audit log.
          </p>
          <div className="button-row">
            <button
              className="primary-button"
              type="button"
              onClick={() =>
                void downloadWorkspaceExport().catch(() =>
                  setMessage('Unable to export workspace data.'),
                )
              }
            >
              Download JSON archive
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() =>
                void downloadWorkspaceExport('contacts', 'csv').catch(() =>
                  setMessage('Unable to export contacts.'),
                )
              }
            >
              Download contacts CSV
            </button>
          </div>
        </section>
      )}
      <section className="workflow-panel settings-sessions">
        <div className="workflow-panel__heading">
          <h2>Active sessions</h2>
        </div>
        {sessions.length === 0 ? (
          <p className="empty-state">No active sessions.</p>
        ) : (
          sessions.map((session) => (
            <article className="settings-session" key={session.id}>
              <div>
                <strong>
                  {session.current ? 'Current session' : 'Signed-in session'}
                </strong>
                <p>
                  {session.user_agent ?? 'Unknown device'} ·{' '}
                  {session.ip_address ?? 'Unknown IP'}
                </p>
              </div>
              {!session.current && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => void removeSession(session.id)}
                >
                  Revoke
                </button>
              )}
            </article>
          ))
        )}
      </section>
      {notifications && (
        <form
          className="workflow-panel auth-form"
          onSubmit={async (event) => {
            event.preventDefault();
            setNotifications(
              await updateNotificationPreferences(notifications),
            );
            setMessage('Notification preferences updated.');
          }}
        >
          <div className="workflow-panel__heading">
            <h2>Notifications</h2>
          </div>
          <label>
            <input
              type="checkbox"
              checked={notifications.in_app_enabled}
              onChange={(event) =>
                setNotifications({
                  ...notifications,
                  in_app_enabled: event.target.checked,
                })
              }
            />
            In-app operational notifications
          </label>
          <label>
            <input
              type="checkbox"
              checked={notifications.email_enabled}
              onChange={(event) =>
                setNotifications({
                  ...notifications,
                  email_enabled: event.target.checked,
                })
              }
            />
            Email notifications (requires configured transactional provider)
          </label>
          <button className="primary-button">Save preferences</button>
        </form>
      )}
      {message && (
        <p className="form-message settings-message" role="status">
          {message}
        </p>
      )}
    </main>
  );
}
