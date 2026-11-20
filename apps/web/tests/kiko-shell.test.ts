import { describe, expect, it, vi } from 'vitest';

import { isCurrent, MORE_NAV, PRIMARY_NAV } from '../components/dashboard-nav';
import { QUICK_ACTIONS } from '../components/kiko/kiko-home';

vi.mock('../lib/auth-client', () => ({
  authFetch: vi.fn(),
  apiFetch: vi.fn(),
  logout: vi.fn(),
}));

// Every dashboard module (as in e2e/dashboard-quality-sweep.spec.ts) stays reachable.
const MODULES = [
  '/dashboard',
  '/dashboard/kiko',
  '/dashboard/commands',
  '/dashboard/tasks',
  '/dashboard/projects',
  '/dashboard/executions',
  '/dashboard/analytics',
  '/dashboard/agents',
  '/dashboard/automations',
  '/dashboard/knowledge',
  '/dashboard/approvals',
  '/dashboard/notifications',
  '/dashboard/codex',
  '/dashboard/email',
  '/dashboard/calendar',
  '/dashboard/crm',
  '/dashboard/marketing',
  '/dashboard/integrations',
  '/dashboard/subscription',
];

describe('Kiko Alive navigation', () => {
  it('keeps every existing module in the rail', () => {
    const links = [...PRIMARY_NAV, ...MORE_NAV].map((item) => item.href);
    for (const route of MODULES) expect(links).toContain(route);
    expect(new Set(links).size).toBe(links.length);
  });

  it('marks the current section, including nested pages and trailing slashes', () => {
    expect(isCurrent('/dashboard/', '/dashboard')).toBe(true);
    expect(isCurrent('/dashboard/commands/abc/', '/dashboard')).toBe(false);
    expect(isCurrent('/dashboard/commands/abc/', '/dashboard/commands')).toBe(
      true,
    );
    expect(isCurrent('/dashboard/crm', '/dashboard/commands')).toBe(false);
  });

  it('connects every quick action to an existing workflow', () => {
    for (const action of QUICK_ACTIONS) {
      const root = action.href.replace(/\/new$/, '');
      expect(MODULES).toContain(root);
    }
  });
});
