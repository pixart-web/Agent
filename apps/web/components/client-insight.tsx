import type { CrmInsight } from '@agent/shared';
import React from 'react';

export function ClientInsight({ insight }: { insight: CrmInsight }) {
  return (
    <article className="agent-card">
      <p className="eyebrow">
        {insight.kind === 'fact' ? 'Verified CRM fact' : 'AI summary'} ·{' '}
        {insight.provenance}
      </p>
      <p>{insight.text}</p>
    </article>
  );
}
