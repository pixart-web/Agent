import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authFetch } from '../lib/auth-client';
import {
  approveAction,
  createTaskAction,
  dispatchAction,
  listApprovals,
  listCommandActivity,
  listExecutions,
} from '../lib/workflow-client';

vi.mock('../lib/auth-client', () => ({ authFetch: vi.fn() }));
const mockedAuthFetch = vi.mocked(authFetch);

function response(body: unknown = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('execution client', () => {
  beforeEach(() => {
    mockedAuthFetch.mockReset();
    mockedAuthFetch.mockImplementation(async () => response());
  });

  it('creates and dispatches a schema-bound action', async () => {
    await createTaskAction('task-1', {
      tool_name: 'internal.echo',
      input_payload: { text: 'Kiko' },
    });
    await dispatchAction('action-1');

    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      1,
      '/api/v1/tasks/task-1/actions',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool_name: 'internal.echo',
          input_payload: { text: 'Kiko' },
        }),
      },
    );
    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      2,
      '/api/v1/actions/action-1/dispatch',
      { method: 'POST' },
    );
  });

  it('submits reinforced red approval confirmation', async () => {
    await approveAction('approval-1', true, 'I understand');

    expect(mockedAuthFetch).toHaveBeenCalledWith(
      '/api/v1/approvals/approval-1/approve',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          confirm_high_risk: true,
          reason: 'I understand',
        }),
      },
    );
  });

  it('filters executions and approvals and loads the audit timeline', async () => {
    await listExecutions({
      status: 'retry_scheduled',
      agent: 'development',
      risk: 'red',
    });
    await listApprovals({ status: 'pending', risk_level: 'yellow' });
    await listCommandActivity('command-1');

    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      1,
      '/api/v1/executions?status=retry_scheduled&agent=development&risk=red',
      {},
    );
    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      2,
      '/api/v1/approvals?status=pending&risk_level=yellow',
      {},
    );
    expect(mockedAuthFetch).toHaveBeenNthCalledWith(
      3,
      '/api/v1/commands/command-1/activity',
      {},
    );
  });
});
