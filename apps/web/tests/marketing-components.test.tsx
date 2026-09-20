import type { TaskAction } from '@agent/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ActionProposalPreview } from '../components/task-agent-panel';

const scheduleAction: TaskAction = {
  id: 'action-marketing',
  task_id: 'task-marketing',
  tool_name: 'marketing.schedule_content',
  tool_version: '1',
  input_payload: {
    content_id: 'content-demo',
    scheduled_for: '2026-09-22T18:00:00Z',
    reason: 'Proposed demo slot',
  },
  risk_level: 'yellow',
  status: 'waiting_approval',
  created_by_type: 'agent',
  created_by_id: null,
  action_fingerprint: 'fingerprint',
  correlation_id: 'correlation',
  created_at: '2026-09-20T10:00:00Z',
  updated_at: '2026-09-20T10:00:00Z',
};

describe('Marketing approval UI', () => {
  it('shows the exact schedule payload and approval requirement', () => {
    const markup = renderToStaticMarkup(
      <ActionProposalPreview action={scheduleAction} />,
    );

    expect(markup).toContain('Schedule Proposed Content');
    expect(markup).toContain('content-demo');
    expect(markup).toContain('2026-09-22T18:00:00Z');
    expect(markup).toContain('Risk: yellow');
    expect(markup).toContain('Requires approval: Yes');
  });

  it('labels publication recording as confirmation, not publishing', () => {
    const markup = renderToStaticMarkup(
      <ActionProposalPreview
        action={{
          ...scheduleAction,
          tool_name: 'marketing.record_publication',
        }}
      />,
    );

    expect(markup).toContain('Record Confirmed Publication');
    expect(markup).not.toContain('Publish Content');
  });
});
