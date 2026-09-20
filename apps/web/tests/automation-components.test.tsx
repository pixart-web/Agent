import type { AutomationRun } from '@agent/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import {
  AutomationPolicyNote,
  AutomationRunSummary,
} from '../components/automation-summary';

const run: AutomationRun = {
  id: 'run-demo',
  automation_id: 'automation-demo',
  trigger_type: 'calendar_event',
  trigger_key: 'event-demo',
  status: 'skipped',
  correlation_id: 'correlation-demo',
  causation_run_id: null,
  depth: 1,
  command_id: null,
  skipped_reason: 'depth_limit',
  error_code: null,
  error_message: null,
  created_at: '2026-09-20T10:00:00Z',
  completed_at: '2026-09-20T10:00:00Z',
  deduplicated: false,
};

describe('Automation governance UI', () => {
  it('states that automation cannot bypass risk and approvals', () => {
    const markup = renderToStaticMarkup(<AutomationPolicyNote />);

    expect(markup).toContain('cannot approve plans');
    expect(markup).toContain('lower risk');
    expect(markup).toContain('untrusted data');
  });

  it('shows loop guardrails without exposing event payloads', () => {
    const markup = renderToStaticMarkup(<AutomationRunSummary run={run} />);

    expect(markup).toContain('depth_limit');
    expect(markup).toContain('correlation-demo');
    expect(markup).not.toContain('event-demo');
  });
});
