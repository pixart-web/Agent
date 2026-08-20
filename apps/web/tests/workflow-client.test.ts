import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authFetch } from '../lib/auth-client';
import {
  approvePlan,
  createCommand,
  generateSupervisorPlan,
  listCommands,
  listPlans,
  regenerateSupervisorPlan,
  transitionTask,
  WorkflowApiError,
} from '../lib/workflow-client';

vi.mock('../lib/auth-client', () => ({
  authFetch: vi.fn(),
}));

const mockedAuthFetch = vi.mocked(authFetch);

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('workflow client', () => {
  beforeEach(() => {
    mockedAuthFetch.mockReset();
  });

  it('creates a command through the authenticated client', async () => {
    mockedAuthFetch.mockResolvedValue(jsonResponse({ id: 'command-1' }, 201));

    await createCommand('Prepare the launch plan');

    expect(mockedAuthFetch).toHaveBeenCalledWith('/api/v1/commands', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: 'Prepare the launch plan' }),
    });
  });

  it('lists filtered commands with pagination', async () => {
    mockedAuthFetch.mockResolvedValue(jsonResponse([]));

    await listCommands({ limit: 20, offset: 40, status: 'planning' });

    expect(mockedAuthFetch).toHaveBeenCalledWith(
      '/api/v1/commands?limit=20&offset=40&status=planning',
      {},
    );
  });

  it('submits an explicit task transition and reason', async () => {
    mockedAuthFetch.mockResolvedValue(jsonResponse({ id: 'task-1' }));

    await transitionTask('task-1', 'blocked', 'Waiting for copy approval');

    expect(mockedAuthFetch).toHaveBeenCalledWith(
      '/api/v1/tasks/task-1/transition',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: 'blocked',
          reason: 'Waiting for copy approval',
        }),
      },
    );
  });

  it('exposes safe API errors to the workflow UI', async () => {
    mockedAuthFetch.mockResolvedValue(
      jsonResponse({ detail: 'Invalid task status transition.' }, 409),
    );

    await expect(transitionTask('task-1', 'completed')).rejects.toEqual(
      new WorkflowApiError('Invalid task status transition.', 409),
    );
  });

  it('generates and regenerates supervisor plans through centralized endpoints', async () => {
    mockedAuthFetch.mockImplementation(async () =>
      jsonResponse({ plan: { id: 'plan-1' } }, 201),
    );

    await generateSupervisorPlan('command-1');
    await regenerateSupervisorPlan('command-1', 'Prefer organic outreach');

    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      1,
      '/api/v1/commands/command-1/generate-plan',
      { method: 'POST' },
    );
    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      2,
      '/api/v1/commands/command-1/regenerate-plan',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback: 'Prefer organic outreach' }),
      },
    );
  });

  it('lists versions and approves a selected plan', async () => {
    mockedAuthFetch.mockImplementation(async () => jsonResponse([]));

    await listPlans('command-1');
    await approvePlan('plan-1');

    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      1,
      '/api/v1/commands/command-1/plans',
      {},
    );
    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      2,
      '/api/v1/plans/plan-1/approve',
      { method: 'POST' },
    );
  });
});
