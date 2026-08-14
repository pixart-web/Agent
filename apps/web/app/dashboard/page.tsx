'use client';

import { AGENT_CATALOG } from '@agent/shared';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import {
  getCurrentUser,
  logout,
  refreshAccessToken,
} from '../../lib/auth-client';
import type { User } from '../../lib/auth-types';

type ApiState = 'checking' | 'online' | 'offline';

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [apiState, setApiState] = useState<ApiState>('checking');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function initialize() {
      try {
        const refreshed = await refreshAccessToken();
        if (!refreshed) {
          router.replace('/login');
          return;
        }
        const currentUser = await getCurrentUser();
        if (!currentUser) {
          router.replace('/login');
          return;
        }
        if (active) {
          setUser(currentUser);
          setLoading(false);
        }
      } catch {
        router.replace('/login');
      }
    }

    async function checkApi() {
      try {
        const response = await fetch(`${apiUrl}/health`);
        if (active) setApiState(response.ok ? 'online' : 'offline');
      } catch {
        if (active) setApiState('offline');
      }
    }

    void initialize();
    void checkApi();
    return () => {
      active = false;
    };
  }, [router]);

  async function handleLogout() {
    await logout();
    router.replace('/login');
  }

  if (loading) {
    return (
      <main className="loading-page">
        <p aria-live="polite">Restoring your secure session…</p>
      </main>
    );
  }

  return (
    <main>
      <header className="dashboard-nav">
        <div>
          <span className="brand-mark">Agent</span>
          <span className="nav-user">
            {user?.full_name} · {user?.email}
          </span>
        </div>
        <button
          className="secondary-button"
          type="button"
          onClick={handleLogout}
        >
          Log out
        </button>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">Pixart operations</p>
          <h1>Agent</h1>
          <p className="subtitle">Pixart AI Operating System</p>
        </div>

        <div
          className={`api-status api-status--${apiState}`}
          aria-live="polite"
        >
          <span className="status-dot" aria-hidden="true" />
          <div>
            <span className="status-label">API status</span>
            <strong>{apiState}</strong>
          </div>
        </div>
      </section>

      <section className="agents" aria-labelledby="agents-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Core team</p>
            <h2 id="agents-title">Agent network</h2>
          </div>
          <span>{AGENT_CATALOG.length} agents configured</span>
        </div>

        <div className="agent-grid">
          {AGENT_CATALOG.map((agent, index) => (
            <article className="agent-card" key={agent.id}>
              <div className="agent-card__topline">
                <span className="agent-index">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="ready-pill">Ready</span>
              </div>
              <h3>{agent.name}</h3>
              <p>{agent.description}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
