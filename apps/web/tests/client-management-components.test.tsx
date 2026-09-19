import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ClientInsight } from '../components/client-insight';

describe('Client 360 insight provenance', () => {
  it('labels database-derived facts as verified CRM facts', () => {
    const markup = renderToStaticMarkup(
      <ClientInsight
        insight={{
          kind: 'fact',
          provenance: 'system_fact',
          text: 'One active project.',
          generated_at: null,
        }}
      />,
    );

    expect(markup).toContain('Verified CRM fact');
    expect(markup).toContain('system_fact');
    expect(markup).not.toContain('AI summary');
  });

  it('labels model output explicitly as an AI summary', () => {
    const markup = renderToStaticMarkup(
      <ClientInsight
        insight={{
          kind: 'model_summary',
          provenance: 'llm',
          text: 'Generated relationship summary.',
          generated_at: '2026-09-19T12:00:00Z',
        }}
      />,
    );

    expect(markup).toContain('AI summary');
    expect(markup).toContain('llm');
    expect(markup).not.toContain('Verified CRM fact');
  });
});
