'use client';

import React, { useEffect, useState } from 'react';

function elapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`;
}

/**
 * Shown while the local model works (about 30–90 s): elapsed time, what is happening and
 * that leaving the page is safe when the work runs on the server.
 */
export function AiProgress({
  since,
  label,
  canLeave = false,
}: {
  since: string | number;
  label: string;
  canLeave?: boolean;
}) {
  const start = typeof since === 'number' ? since : Date.parse(since);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const seconds = Math.max(0, Math.floor((now - start) / 1000));
  return (
    <div className="ai-progress" role="status" aria-live="polite">
      <div className="ai-progress__track" aria-hidden="true">
        <span className="ai-progress__bar" />
      </div>
      <p className="ai-progress__label">
        {label} <span className="ai-progress__time">{elapsed(seconds)}</span>
      </p>
      <p className="form-hint">
        O modelo de IA corre localmente e costuma demorar entre 30 e 90
        segundos.
        {canLeave &&
          ' Podes sair desta página: o trabalho continua e o resultado aparece quando voltares.'}
      </p>
    </div>
  );
}
