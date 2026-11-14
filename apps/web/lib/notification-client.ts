import { authFetch } from './auth-client';

export type Notification = {
  id: string;
  kind: string;
  title: string;
  body: string;
  href: string | null;
  read_at: string | null;
  created_at: string;
};

export type NotificationPreferences = {
  in_app_enabled: boolean;
  email_enabled: boolean;
  enabled_kinds: string[];
};

async function json<T>(response: Response): Promise<T> {
  if (!response.ok)
    throw new Error(`Notification request failed (${response.status})`);
  return (await response.json()) as T;
}

export function listNotifications(): Promise<{
  notifications: Notification[];
  unread_count: number;
}> {
  return authFetch('/api/v1/notifications').then((response) =>
    json<{ notifications: Notification[]; unread_count: number }>(response),
  );
}

export async function markNotificationRead(id: string): Promise<void> {
  const response = await authFetch(
    `/api/v1/notifications/${encodeURIComponent(id)}/read`,
    {
      method: 'POST',
    },
  );
  if (!response.ok) throw new Error('Unable to mark notification read');
}

export async function markAllNotificationsRead(): Promise<void> {
  const response = await authFetch('/api/v1/notifications/read-all', {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Unable to mark notifications read');
}

export function getNotificationPreferences(): Promise<NotificationPreferences> {
  return authFetch('/api/v1/notifications/preferences').then((response) =>
    json<NotificationPreferences>(response),
  );
}

export function updateNotificationPreferences(
  value: NotificationPreferences,
): Promise<NotificationPreferences> {
  return authFetch('/api/v1/notifications/preferences', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(value),
  }).then((response) => json<NotificationPreferences>(response));
}
