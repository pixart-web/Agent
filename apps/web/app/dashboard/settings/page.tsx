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
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function SettingsPage() {
  const router = useRouter();
  const { user, loading } = useAuthenticatedUser();
  const [fullName, setFullName] = useState('');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!user) return;
    setFullName(user.full_name);
    void listSessions().then(setSessions).catch(() => setMessage('Unable to load sessions.'));
  }, [user]);

  if (loading || !user) return <main className="loading-page">Loading settings…</main>;

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    try {
      await updateProfile(fullName.trim());
      setMessage('Profile updated.');
    } catch (error) {
      setMessage(error instanceof AuthClientError ? error.message : 'Unable to update profile.');
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    try {
      await changePassword(currentPassword, newPassword);
      router.replace('/login');
    } catch (error) {
      setMessage(error instanceof AuthClientError ? error.message : 'Unable to change password.');
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
        <div><p className="eyebrow">Account</p><h1>Settings</h1></div>
      </section>
      <section className="workflow-grid">
        <form className="workflow-panel auth-form" onSubmit={saveProfile}>
          <div className="workflow-panel__heading"><h2>Profile</h2></div>
          <label>Full name<input value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>
          <label>Email<input value={user.email} disabled /></label>
          <button className="primary-button" type="submit">Save profile</button>
        </form>
        <form className="workflow-panel auth-form" onSubmit={savePassword}>
          <div className="workflow-panel__heading"><h2>Change password</h2></div>
          <label>Current password<input type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label>
          <label>New password<input type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
          <button className="primary-button" type="submit">Change password</button>
        </form>
      </section>
      <section className="workflow-panel settings-sessions">
        <div className="workflow-panel__heading"><h2>Active sessions</h2></div>
        {sessions.length === 0 ? <p className="empty-state">No active sessions.</p> : sessions.map((session) => (
          <article className="settings-session" key={session.id}>
            <div><strong>{session.current ? 'Current session' : 'Signed-in session'}</strong><p>{session.user_agent ?? 'Unknown device'} · {session.ip_address ?? 'Unknown IP'}</p></div>
            {!session.current && <button className="secondary-button" type="button" onClick={() => void removeSession(session.id)}>Revoke</button>}
          </article>
        ))}
      </section>
      {message && <p className="form-message settings-message" role="status">{message}</p>}
    </main>
  );
}
