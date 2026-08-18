import type { TaskDetail } from '@agent/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { TaskExecutionPanel } from '../components/task-execution-panel';

vi.mock('../lib/workflow-client', () => ({
  createTaskAction: vi.fn(),
  dispatchAction: vi.fn(),
  listActionExecutions: vi.fn().mockResolvedValue([]),
  listCommandActivity: vi.fn().mockResolvedValue([]),
  listTaskActions: vi.fn().mockResolvedValue([]),
  WorkflowApiError: class WorkflowApiError extends Error {},
}));

const task: TaskDetail = {
  id: 'task-1',
  plan_id: 'plan-1',
  agent_id: 'development',
  title: 'Review critical deployment simulation',
  instructions: 'Use only the safe simulator.',
  status: 'ready',
  priority: 'high',
  risk_level: 'red',
  sequence: 1,
  created_at: '2026-08-18T10:00:00Z',
  updated_at: '2026-08-18T10:00:00Z',
  started_at: null,
  completed_at: null,
  error_message: null,
  history: [],
};

describe('execution UI', () => {
  it('shows registered tools, action composer, attempts and activity timeline', () => {
    const markup = renderToStaticMarkup(
      <TaskExecutionPanel commandId="command-1" tasks={[task]} />,
    );

    expect(markup).toContain('Execution Engine');
    expect(markup).toContain('internal.echo');
    expect(markup).toContain('internal.simulate_critical_action');
    expect(markup).toContain('Create &amp; dispatch');
    expect(markup).toContain('Activity timeline');
  });
});
