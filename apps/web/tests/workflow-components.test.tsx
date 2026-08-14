import type { Command, Plan, SupervisorRun, WorkflowTask } from '@agent/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { CommandDetail } from '../components/command-detail';
import { CommandList } from '../components/command-list';
import { SupervisorPlanReview } from '../components/supervisor-plan-review';

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
  version: 1,
  is_current: true,
  title: 'Launch plan',
  objective: 'Coordinate the initial product launch.',
  reasoning_summary: 'Research and content preparation are separated.',
  rejection_reason: null,
  status: 'draft',
  created_at: '2026-08-14T10:01:00Z',
  updated_at: '2026-08-14T10:01:00Z',
  approved_at: null,
  approved_by_user_id: null,
};

const run: SupervisorRun = {
  id: 'run-1',
  command_id: command.id,
  user_id: command.user_id,
  status: 'completed',
  provider: 'openai',
  model: 'test-model',
  prompt_version: 'supervisor-plan-v1',
  input_tokens: 80,
  output_tokens: 40,
  total_tokens: 120,
  estimated_cost: null,
  currency: null,
  latency_ms: 350,
  request_id: null,
  error_code: null,
  error_message: null,
  user_feedback: null,
  created_at: '2026-08-14T10:00:30Z',
  completed_at: '2026-08-14T10:01:00Z',
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

  it('renders the generate button and its loading state', () => {
    const baseProps = {
      plan: null,
      tasks: [],
      versions: [],
      run: null,
      agents: [],
      error: '',
      feedback: '',
      onFeedbackChange: () => undefined,
      onGenerate: () => undefined,
      onApprove: () => undefined,
      onRegenerate: () => undefined,
    };
    const idle = renderToStaticMarkup(
      <SupervisorPlanReview {...baseProps} planning={false} />,
    );
    const loading = renderToStaticMarkup(
      <SupervisorPlanReview {...baseProps} planning />,
    );

    expect(idle).toContain('Gerar plano com Supervisor');
    expect(loading).toContain('Supervisor está a preparar o plano');
    expect(loading).toContain('disabled');
  });

  it('renders proposal, approval, feedback, versions and usage metadata', () => {
    const rejectedVersion = {
      ...plan,
      id: 'plan-old',
      version: 0,
      is_current: false,
      status: 'cancelled' as const,
      rejection_reason: 'Use an organic-first approach.',
    };
    const markup = renderToStaticMarkup(
      <SupervisorPlanReview
        plan={plan}
        tasks={[task]}
        versions={[plan, rejectedVersion]}
        run={run}
        agents={[
          {
            id: 'marketing',
            name: 'Marketing',
            description: 'Campaign operations',
            status: 'ready',
          },
        ]}
        planning={false}
        error=""
        feedback="Start organically"
        onFeedbackChange={() => undefined}
        onGenerate={() => undefined}
        onApprove={() => undefined}
        onRegenerate={() => undefined}
      />,
    );

    expect(markup).toContain('Plano proposto pelo Supervisor');
    expect(markup).toContain('Aprovar plano');
    expect(markup).toContain('Pedir alterações');
    expect(markup).toContain('Start organically');
    expect(markup).toContain('Plan v0');
    expect(markup).toContain('test-model');
    expect(markup).toContain('120');
  });

  it('renders a safe supervisor error', () => {
    const markup = renderToStaticMarkup(
      <SupervisorPlanReview
        plan={null}
        tasks={[]}
        versions={[]}
        run={null}
        agents={[]}
        planning={false}
        error="AI provider is unavailable"
        feedback=""
        onFeedbackChange={() => undefined}
        onGenerate={() => undefined}
        onApprove={() => undefined}
        onRegenerate={() => undefined}
      />,
    );

    expect(markup).toContain('role="alert"');
    expect(markup).toContain('AI provider is unavailable');
  });
});
