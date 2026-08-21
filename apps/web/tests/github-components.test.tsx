import type { TaskAction } from '@agent/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ActionProposalPreview } from '../components/task-agent-panel';

const action: TaskAction = {
  id: 'action-1',
  task_id: 'task-1',
  tool_name: 'github.create_issue',
  tool_version: '1',
  input_payload: {
    repository: 'pixart-web/Agent',
    title: 'Add password recovery',
  },
  risk_level: 'yellow',
  status: 'waiting_approval',
  created_by_type: 'agent',
  created_by_id: null,
  action_fingerprint: 'fingerprint',
  correlation_id: 'correlation',
  created_at: '2026-08-20T10:00:00Z',
  updated_at: '2026-08-20T10:00:00Z',
};

describe('GitHub action UI', () => {
  it('shows repository, title, risk and approval requirement', () => {
    const markup = renderToStaticMarkup(
      <ActionProposalPreview action={action} />,
    );

    expect(markup).toContain('Create GitHub Issue');
    expect(markup).toContain('Repository: pixart-web/Agent');
    expect(markup).toContain('Title: Add password recovery');
    expect(markup).toContain('Risk: yellow');
    expect(markup).toContain('Requires approval: Yes');
  });
});
