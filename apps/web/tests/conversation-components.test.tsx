import type { ConversationOperation } from '@agent/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ConversationOperationStatus } from '../components/conversation-operation-status';

const operation: ConversationOperation = {
  command: {
    id: 'command-1',
    workspace_id: 'workspace-1',
    user_id: 'user-1',
    conversation_id: 'conversation-1',
    duplicated_from_id: null,
    input: 'Prepare a campaign',
    status: 'in_progress',
    created_at: '2026-10-11T09:00:00Z',
    updated_at: '2026-10-11T09:01:00Z',
    completed_at: null,
    archived_at: null,
  },
  plan: {
    id: 'plan-1',
    title: 'Campaign plan',
    objective: 'Generate qualified demand',
    status: 'in_progress',
  },
  supervisor_status: 'completed',
  task_counts: { completed: 2, waiting_approval: 1 },
  pending_approvals: 1,
  latest_error: null,
};

describe('conversation operation status', () => {
  it('renders workflow state and pending approvals', () => {
    const markup = renderToStaticMarkup(
      <ConversationOperationStatus operation={operation} />,
    );

    expect(markup).toContain('in progress');
    expect(markup).toContain('Supervisor: completed');
    expect(markup).toContain('Campaign plan');
    expect(markup).toContain('2 completed · 1 waiting approval');
    expect(markup).toContain('1 aprovação pendente');
  });

  it('renders a safe operational error', () => {
    const markup = renderToStaticMarkup(
      <ConversationOperationStatus
        operation={{
          ...operation,
          latest_error: 'Provider delivery failed safely',
        }}
      />,
    );

    expect(markup).toContain('role="alert"');
    expect(markup).toContain('Provider delivery failed safely');
  });
});
