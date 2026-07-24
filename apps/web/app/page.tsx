'use client';

import { AGENT_CATALOG } from '@agent/shared';
import { useEffect, useState } from 'react';

type ApiState = 'checking' | 'online' | 'offline';

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export default function Home() {
  const [apiState, setApiState] = useState<ApiState>('checking');

  useEffect(() => {
    const controller = new AbortController();

    async function checkApi() {
      try {
        const response = await fetch(`${apiUrl}/health`, {
          signal: controller.signal,
        });
        setApiState(response.ok ? 'online' : 'offline');
      } catch {
        if (!controller.signal.aborted) {
          setApiState('offline');
        }
      }
    }

    void checkApi();
    return () => controller.abort();
  }, []);

  return (
    <main>
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
