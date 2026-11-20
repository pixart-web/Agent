import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { AiErrorNotice } from '../components/ai-error-notice';
import { aiErrorHint } from '../lib/ai-errors';

describe('local AI error hints', () => {
  it('explains the runtime, model, timeout and worker problems', () => {
    expect(aiErrorHint('Local AI runtime is not reachable')).toContain(
      'Ollama',
    );
    expect(
      aiErrorHint("Local AI model 'gemma4:12b-it-qat' is not installed"),
    ).toContain('ollama pull gemma4:12b-it-qat');
    expect(aiErrorHint('Local AI model timed out')).toContain('demorou');
    expect(
      aiErrorHint(
        'Background agent runs are unavailable. Try again in a moment.',
      ),
    ).toContain('segundo plano');
  });

  it('adds nothing to unrelated errors', () => {
    expect(aiErrorHint('Task not found')).toBeNull();
    expect(aiErrorHint(null)).toBeNull();
    const markup = renderToStaticMarkup(
      <AiErrorNotice message="Task not found" />,
    );
    expect(markup).not.toContain('ai-error-hint');
  });

  it('shows the hint under the message', () => {
    const markup = renderToStaticMarkup(
      <AiErrorNotice message="Local AI runtime is not reachable" />,
    );
    expect(markup).toContain('role="alert"');
    expect(markup).toContain('ai-error-hint');
  });
});
