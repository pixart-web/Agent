import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authFetch } from '../lib/auth-client';
import {
  getAgentOverview,
  listAgentRuns,
  rerunAgent,
  runAgent,
} from '../lib/workflow-client';

vi.mock('../lib/auth-client', () => ({ authFetch: vi.fn() }));
const mockedAuthFetch = vi.mocked(authFetch);

describe('specialized agent client', () => {
  beforeEach(() => {
    mockedAuthFetch.mockReset();
    mockedAuthFetch.mockImplementation(
      async () =>
        new Response(JSON.stringify({ actions: [], run: {} }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
    );
  });

  it('runs and reruns an assigned agent without an execution call', async () => {
    await runAgent('task-1');
    await rerunAgent('task-1', 'More direct');
    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      1,
      '/api/v1/tasks/task-1/run-agent',
      { method: 'POST' },
    );
    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      2,
      '/api/v1/tasks/task-1/rerun-agent',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('loads private run history and overview', async () => {
    await listAgentRuns('task-1');
    await getAgentOverview('marketing');
    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      1,
      '/api/v1/tasks/task-1/agent-runs',
      {},
    );
    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      2,
      '/api/v1/agents/marketing/overview',
      {},
    );
  });
});
