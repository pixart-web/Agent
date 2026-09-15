import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authFetch } from '../lib/auth-client';
import {
  getAgentOverview,
  connectEmail,
  disconnectEmail,
  getEmailIntegrationStatus,
  getEmailMessage,
  getGitHubIntegrationStatus,
  listEmailAccounts,
  listEmailMessages,
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

  it('loads safe GitHub integration status', async () => {
    await getGitHubIntegrationStatus();
    expect(mockedAuthFetch).toHaveBeenCalledWith(
      '/api/v1/integrations/github/status',
      {},
    );
  });

  it('uses only safe email integration and mailbox endpoints', async () => {
    mockedAuthFetch.mockImplementation(
      async (path) =>
        new Response(
          JSON.stringify(
            path.toString().endsWith('/accounts') ? { accounts: [] } : {},
          ),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
    );
    await getEmailIntegrationStatus();
    await listEmailAccounts();
    await connectEmail();
    await disconnectEmail('account-1');
    await listEmailMessages('account-1');
    await getEmailMessage('account-1', 'message/1');

    expect(mockedAuthFetch).toHaveBeenCalledWith(
      '/api/v1/integrations/email/status',
      {},
    );
    expect(mockedAuthFetch).toHaveBeenCalledWith(
      '/api/v1/email/messages/message%2F1?account_id=account-1',
      {},
    );
    expect(JSON.stringify(mockedAuthFetch.mock.calls)).not.toContain('token');
  });
});
