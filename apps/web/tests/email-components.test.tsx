import type { TaskAction } from '@agent/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ActionProposalPreview } from '../components/task-agent-panel';

const action: TaskAction = {
  id: 'action-email',
  task_id: 'task-1',
  tool_name: 'email.send',
  tool_version: '2',
  input_payload: {
    account_id: 'account-1',
    to: [{ address: 'customer@example.net' }],
    subject: 'Approved subject',
    body: 'Complete approved body',
  },
  risk_level: 'yellow',
  status: 'waiting_approval',
  created_by_type: 'agent',
  created_by_id: null,
  action_fingerprint: 'fingerprint',
  correlation_id: 'correlation',
  created_at: '2026-08-23T10:00:00Z',
  updated_at: '2026-08-23T10:00:00Z',
};

describe('email action UI', () => {
  it('shows the governed email target, subject, risk and approval requirement', () => {
    const markup = renderToStaticMarkup(
      <ActionProposalPreview action={action} />,
    );

    expect(markup).toContain('Send Email');
    expect(markup).toContain('Account: account-1');
    expect(markup).toContain('Subject: Approved subject');
    expect(markup).toContain('Recipients: customer@example.net');
    expect(markup).toContain('Risk: yellow');
    expect(markup).toContain('Requires approval: Yes');
    expect(markup).not.toContain('Complete approved body');
  });
});
