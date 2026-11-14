import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authFetch } from '../lib/auth-client';
import {
  approvePlan,
  addApprovalComment,
  createTaskDependency,
  createProject,
  deleteTaskDependency,
  createCommand,
  generateSupervisorPlan,
  listCommands,
  listProjects,
  listPlans,
  listWorkspaceTasks,
  getApprovalDetail,
  scheduleTask,
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

  it('lists workspace tasks with operational filters', async () => {
    mockedAuthFetch.mockResolvedValue(jsonResponse([]));

    await listWorkspaceTasks({
      search: 'launch',
      status: 'blocked',
      priority: 'urgent',
      agentId: 'development',
      limit: 50,
    });

    expect(mockedAuthFetch).toHaveBeenCalledWith(
      '/api/v1/tasks?status=blocked&priority=urgent&agent_id=development&search=launch&limit=50',
      {},
    );
  });

  it('creates and filters workspace projects', async () => {
    mockedAuthFetch.mockImplementation(async () => jsonResponse([], 201));

    await createProject({ name: 'Launch', status: 'active' });
    await listProjects({ status: 'blocked', search: 'retail' });

    expect(mockedAuthFetch).toHaveBeenNthCalledWith(1, '/api/v1/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'Launch', status: 'active' }),
    });
    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      2,
      '/api/v1/projects?status=blocked&search=retail',
      {},
    );
  });

  it('manages dependencies and evaluates scheduling', async () => {
    mockedAuthFetch.mockImplementation(async () =>
      jsonResponse({ id: 'dependency-1' }, 201),
    );

    await createTaskDependency('task-1', 'task-2');
    await scheduleTask('task-1');

    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      1,
      '/api/v1/tasks/task-1/dependencies',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ depends_on_task_id: 'task-2' }),
      },
    );
    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      2,
      '/api/v1/tasks/task-1/schedule',
      { method: 'POST' },
    );
  });

  it('removes a dependency without parsing an empty response', async () => {
    mockedAuthFetch.mockResolvedValue(new Response(null, { status: 204 }));

    await deleteTaskDependency('task-1', 'dependency-1');

    expect(mockedAuthFetch).toHaveBeenCalledWith(
      '/api/v1/tasks/task-1/dependencies/dependency-1',
      { method: 'DELETE' },
    );
  });

  it('loads approval evidence and adds a comment', async () => {
    mockedAuthFetch.mockImplementation(async () =>
      jsonResponse({ id: 'item-1' }),
    );

    await getApprovalDetail('approval-1');
    await addApprovalComment('approval-1', 'Check the recipient');

    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      1,
      '/api/v1/approvals/approval-1/detail',
      {},
    );
    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      2,
      '/api/v1/approvals/approval-1/comments',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: 'Check the recipient' }),
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
