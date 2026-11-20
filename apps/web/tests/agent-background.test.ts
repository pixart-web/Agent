import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authFetch } from '../lib/auth-client';
import {
  isAgentRunActive,
  startAgentRun,
  waitForAgentRun,
  WorkflowApiError,
} from '../lib/workflow-client';

vi.mock('../lib/auth-client', () => ({ authFetch: vi.fn() }));
const mockedAuthFetch = vi.mocked(authFetch);

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const run = (status: string) => ({ id: 'run-1', status, error_message: null });

describe('background agent runs', () => {
  beforeEach(() => mockedAuthFetch.mockReset());

  it('starts a run, with feedback only when given', async () => {
    mockedAuthFetch.mockImplementation(async () => json(run('running'), 202));
    await startAgentRun('t1');
    await startAgentRun('t1', 'Be brief');
    const bodies = mockedAuthFetch.mock.calls.map(([path, init]) => [
      path,
      (init as RequestInit).body,
    ]);
    expect(bodies).toEqual([
      ['/api/v1/tasks/t1/agent-runs', '{}'],
      ['/api/v1/tasks/t1/agent-runs', JSON.stringify({ feedback: 'Be brief' })],
    ]);
  });

  it('treats pending and running as active', () => {
    expect(isAgentRunActive(run('running') as never)).toBe(true);
    expect(isAgentRunActive(run('pending') as never)).toBe(true);
    expect(isAgentRunActive(run('failed') as never)).toBe(false);
  });

  it('polls until the run has finished', async () => {
    const answers = [[run('running')], [run('completed')]];
    mockedAuthFetch.mockImplementation(async () => json(answers.shift()));
    const sleep = vi.fn(async () => undefined);
    const finished = await waitForAgentRun('t1', 'run-1', { sleep });
    expect(finished?.status).toBe('completed');
    expect(sleep).toHaveBeenCalledTimes(1);
  });

  it('gives up after the time limit', async () => {
    mockedAuthFetch.mockImplementation(async () => json([run('running')]));
    await expect(
      waitForAgentRun('t1', 'run-1', {
        timeoutMs: -1,
        sleep: async () => undefined,
      }),
    ).rejects.toBeInstanceOf(WorkflowApiError);
  });
});
