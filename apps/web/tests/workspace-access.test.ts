import { beforeEach, describe, expect, it, vi } from 'vitest';

const getWorkspaceSettings = vi.fn();
vi.mock('../lib/workspace-settings-client', () => ({
  getWorkspaceSettings: () => getWorkspaceSettings(),
}));

import {
  canEdit,
  canManage,
  loadWorkspaceRole,
  resetWorkspaceRole,
} from '../lib/workspace-access';

describe('workspace access', () => {
  beforeEach(() => {
    getWorkspaceSettings.mockReset();
    resetWorkspaceRole();
  });

  it('lets every role except viewers edit, and only owners and admins manage', () => {
    expect(canEdit('viewer')).toBe(false);
    for (const role of ['owner', 'admin', 'manager', 'member'] as const) {
      expect(canEdit(role)).toBe(true);
    }
    expect(canManage('owner')).toBe(true);
    expect(canManage('admin')).toBe(true);
    expect(canManage('manager')).toBe(false);
    expect(canManage('member')).toBe(false);
    expect(canManage('viewer')).toBe(false);
    // Unknown role: show editing controls; the API still enforces permissions.
    expect(canEdit(null)).toBe(true);
    expect(canManage(null)).toBe(false);
  });

  it('shares one settings request between components and refreshes it later', async () => {
    getWorkspaceSettings.mockResolvedValue({ role: 'viewer' });
    const first = loadWorkspaceRole(1_000);
    const second = loadWorkspaceRole(2_000);
    expect(await first).toBe('viewer');
    expect(await second).toBe('viewer');
    expect(getWorkspaceSettings).toHaveBeenCalledTimes(1);
    getWorkspaceSettings.mockResolvedValue({ role: 'member' });
    expect(await loadWorkspaceRole(10_000)).toBe('member');
    expect(getWorkspaceSettings).toHaveBeenCalledTimes(2);
  });

  it('treats an unavailable role as unknown instead of failing', async () => {
    getWorkspaceSettings.mockRejectedValue(new Error('offline'));
    expect(await loadWorkspaceRole(1_000)).toBeNull();
  });
});
