import type { TaskDetail } from '@agent/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { TaskAgentPanel } from '../components/task-agent-panel';

vi.mock('../lib/workflow-client', () => ({
  listAgentRuns: vi.fn().mockResolvedValue([]),
  rerunAgent: vi.fn(),
  runAgent: vi.fn(),
  WorkflowApiError: class WorkflowApiError extends Error {},
}));

const task: TaskDetail = {
  id: 'task-1',
  plan_id: 'plan-1',
  agent_id: 'marketing',
  title: 'Prepare restaurant campaign',
  instructions: 'Prepare actions',
  status: 'ready',
  priority: 'normal',
  risk_level: 'green',
  sequence: 1,
  created_at: '2026-08-18T10:00:00Z',
  updated_at: '2026-08-18T10:00:00Z',
  started_at: null,
  completed_at: null,
  error_message: null,
  history: [],
};

describe('specialized agent UI', () => {
  it('shows assignment and keeps proposals separate from execution', () => {
    const markup = renderToStaticMarkup(<TaskAgentPanel tasks={[task]} />);
    expect(markup).toContain('Specialized agents');
    expect(markup).toContain('marketing');
    expect(markup).toContain('Ask agent to prepare actions');
  });
});
