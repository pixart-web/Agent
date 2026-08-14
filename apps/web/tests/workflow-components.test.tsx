import type { Command, Plan, WorkflowTask } from '@agent/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { CommandDetail } from '../components/command-detail';
import { CommandList } from '../components/command-list';

const command: Command = {
  id: 'command-1',
  user_id: 'user-1',
  input: 'Prepare the product launch',
  status: 'planning',
  created_at: '2026-08-14T10:00:00Z',
  updated_at: '2026-08-14T10:00:00Z',
  completed_at: null,
};

const plan: Plan = {
  id: 'plan-1',
  command_id: command.id,
  title: 'Launch plan',
  objective: 'Coordinate the initial product launch.',
  status: 'draft',
  created_at: '2026-08-14T10:01:00Z',
  updated_at: '2026-08-14T10:01:00Z',
};

const task: WorkflowTask = {
  id: 'task-1',
  plan_id: plan.id,
  agent_id: 'marketing',
  title: 'Draft campaign copy',
  instructions: 'Create the first reviewed campaign draft.',
  status: 'waiting_approval',
  priority: 'high',
  risk_level: 'yellow',
  sequence: 1,
  created_at: '2026-08-14T10:02:00Z',
  updated_at: '2026-08-14T10:02:00Z',
  started_at: '2026-08-14T10:03:00Z',
  completed_at: null,
  error_message: null,
};

describe('workflow components', () => {
  it('renders command status and task progress in the list', () => {
    const markup = renderToStaticMarkup(
      <CommandList
        commands={[command]}
        progress={{ [command.id]: { completed: 2, total: 3 } }}
      />,
    );

    expect(markup).toContain('Prepare the product launch');
    expect(markup).toContain('planning');
    expect(markup).toContain('2/3 tasks');
    expect(markup).toContain('/dashboard/commands/command-1');
  });

  it('renders the command, plan, task and principal workflow states', () => {
    const markup = renderToStaticMarkup(
      <CommandDetail
        command={command}
        plan={plan}
        tasks={[task]}
        agents={[
          {
            id: 'marketing',
            name: 'Marketing',
            description: 'Campaign operations',
            status: 'ready',
          },
        ]}
      />,
    );

    expect(markup).toContain('Launch plan');
    expect(markup).toContain('Draft campaign copy');
    expect(markup).toContain('waiting approval');
    expect(markup).toContain('Marketing');
    expect(markup).toContain('high');
    expect(markup).toContain('yellow');
  });

  it('renders an empty command state', () => {
    const markup = renderToStaticMarkup(<CommandList commands={[]} />);

    expect(markup).toContain('No commands yet');
  });
});
