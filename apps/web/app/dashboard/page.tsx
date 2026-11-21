'use client';

import React from 'react';

import { DashboardNav } from '../../components/dashboard-nav';
import { KikoHome } from '../../components/kiko/kiko-home';
import { KikoAvatar } from '../../components/kiko/kiko-avatar';
import { useAuthenticatedUser } from '../../lib/use-authenticated-user';

export default function DashboardPage() {
  const { user, loading } = useAuthenticatedUser();

  if (loading || !user) {
    return (
      <main className="loading-page kiko-boot">
        <KikoAvatar state="sleeping" size={96} decorative />
        <p aria-live="polite">A restaurar a sessão segura…</p>
      </main>
    );
  }

  return (
    <main className="kiko-page kiko-page--home">
      <DashboardNav user={user} />
      <KikoHome user={user} />
    </main>
  );
}
