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
import { label, serverText } from '../../../lib/labels';

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
      void refresh().catch(() =>
        setError('Não foi possível carregar as notificações.'),
      );
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">A carregar as notificações…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Caixa operacional</p>
          <h1>Notificações</h1>
          <p>
            {unread} por ler · geradas a partir do estado guardado do workspace.
          </p>
        </div>
        <button
          className="secondary-button"
          disabled={!unread}
          onClick={() => void markAllNotificationsRead().then(refresh)}
        >
          Marcar tudo como lido
        </button>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <section className="workflow-panel">
        <div className="activity-list">
          {items.map((item) => (
            <article className="activity-item" key={item.id}>
              <p className="eyebrow">
                {label(item.kind)} · {item.read_at ? 'read' : 'unread'}
              </p>
              <h2>{serverText(item.title)}</h2>
              <p>{item.body}</p>
              <p>{new Date(item.created_at).toLocaleString('pt-PT')}</p>
              <div className="button-row">
                {item.href && (
                  <Link href={item.href}>Abrir trabalho relacionado</Link>
                )}
                {!item.read_at && (
                  <button
                    className="text-button"
                    onClick={() =>
                      void markNotificationRead(item.id).then(refresh)
                    }
                  >
                    Marcar como lido
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
        {!items.length && (
          <p className="empty-state">Ainda sem notificações.</p>
        )}
      </section>
    </main>
  );
}
