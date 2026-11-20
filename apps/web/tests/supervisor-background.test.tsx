import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authFetch } from '../lib/auth-client';
import {
  startSupervisorRun,
  waitForSupervisorRun,
  WorkflowApiError,
} from '../lib/workflow-client';
import { AiProgress } from '../components/ai-progress';

vi.mock('../lib/auth-client', () => ({ authFetch: vi.fn() }));
const mockedAuthFetch = vi.mocked(authFetch);

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const run = (status: string) => ({ id: 'run-1', status, error_message: null });

describe('background Supervisor planning', () => {
  beforeEach(() => mockedAuthFetch.mockReset());

  it('starts a run, with feedback only when revising', async () => {
    mockedAuthFetch.mockImplementation(async () => json(run('running'), 202));
    await startSupervisorRun('c1');
    await startSupervisorRun('c1', 'Focus on Lisbon');
    const bodies = mockedAuthFetch.mock.calls.map(([path, init]) => [
      path,
      (init as RequestInit).body,
    ]);
    expect(bodies).toEqual([
      ['/api/v1/commands/c1/supervisor-runs', '{}'],
      [
        '/api/v1/commands/c1/supervisor-runs',
        JSON.stringify({ feedback: 'Focus on Lisbon' }),
      ],
    ]);
  });

  it('polls until the run has finished', async () => {
    const answers = [[run('running')], [run('running')], [run('completed')]];
    mockedAuthFetch.mockImplementation(async () => json(answers.shift()));
    const sleep = vi.fn(async () => undefined);
    const finished = await waitForSupervisorRun('c1', 'run-1', { sleep });
    expect(finished?.status).toBe('completed');
    expect(sleep).toHaveBeenCalledTimes(2);
  });

  it('stops when the page goes away and gives up after the time limit', async () => {
    mockedAuthFetch.mockImplementation(async () => json([run('running')]));
    let cancelled = false;
    const stopped = waitForSupervisorRun('c1', 'run-1', {
      isCancelled: () => cancelled,
      sleep: async () => {
        cancelled = true;
      },
    });
    expect(await stopped).toBeNull();

    await expect(
      waitForSupervisorRun('c1', 'run-1', {
        timeoutMs: -1,
        sleep: async () => undefined,
      }),
    ).rejects.toBeInstanceOf(WorkflowApiError);
  });

  it('shows elapsed time and that leaving the page is safe', () => {
    const html = renderToStaticMarkup(
      <AiProgress
        since={Date.now() - 75_000}
        label="O Supervisor está a preparar o plano…"
        canLeave
      />,
    );
    expect(html).toContain('role="status"');
    expect(html).toContain('1:15');
    expect(html).toContain('Podes sair desta página');
  });
});
