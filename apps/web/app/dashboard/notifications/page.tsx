'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type Notification,
} from '../../../lib/notification-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function NotificationsPage() {
  const { user, loading } = useAuthenticatedUser();
  const [items, setItems] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState('');

  async function refresh() {
    const value = await listNotifications();
    setItems(value.notifications);
    setUnread(value.unread_count);
  }

  useEffect(() => {
    if (user)
      void refresh().catch(() => setError('Unable to load notifications.'));
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">Loading notifications…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Operational inbox</p>
          <h1>Notifications</h1>
          <p>{unread} unread · generated from persisted workspace state.</p>
        </div>
        <button
          className="secondary-button"
          disabled={!unread}
          onClick={() => void markAllNotificationsRead().then(refresh)}
        >
          Mark all read
        </button>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <section className="workflow-panel">
        <div className="activity-list">
          {items.map((item) => (
            <article className="activity-item" key={item.id}>
              <p className="eyebrow">
                {item.kind.replaceAll('_', ' ')} ·{' '}
                {item.read_at ? 'read' : 'unread'}
              </p>
              <h2>{item.title}</h2>
              <p>{item.body}</p>
              <p>{new Date(item.created_at).toLocaleString()}</p>
              <div className="button-row">
                {item.href && <Link href={item.href}>Open related work</Link>}
                {!item.read_at && (
                  <button
                    className="text-button"
                    onClick={() =>
                      void markNotificationRead(item.id).then(refresh)
                    }
                  >
                    Mark read
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
        {!items.length && <p className="empty-state">No notifications yet.</p>}
      </section>
    </main>
  );
}
