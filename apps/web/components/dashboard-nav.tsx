'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

import { logout } from '../lib/auth-client';
import type { User } from '../lib/auth-types';

export function DashboardNav({ user }: { user: User }) {
  const router = useRouter();
  const pathname = usePathname() ?? '';
  const current = (href: string): 'page' | undefined => {
    const active =
      href === '/dashboard'
        ? pathname === '/dashboard' || pathname === '/dashboard/'
        : pathname === href || pathname.startsWith(`${href}/`);
    return active ? 'page' : undefined;
  };

  async function handleLogout() {
    await logout();
    router.replace('/login');
  }

  return (
    <header className="dashboard-nav">
      <div>
        <Link className="brand-mark" href="/dashboard">
          Kiko
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/kiko"
          aria-current={current('/dashboard/kiko')}
        >
          Kiko AI
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/commands"
          aria-current={current('/dashboard/commands')}
        >
          Commands
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/tasks"
          aria-current={current('/dashboard/tasks')}
        >
          Tasks
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/projects"
          aria-current={current('/dashboard/projects')}
        >
          Projects
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/executions"
          aria-current={current('/dashboard/executions')}
        >
          Executions
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/analytics"
          aria-current={current('/dashboard/analytics')}
        >
          Analytics
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/agents"
          aria-current={current('/dashboard/agents')}
        >
          Agents
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/automations"
          aria-current={current('/dashboard/automations')}
        >
          Automations
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/knowledge"
          aria-current={current('/dashboard/knowledge')}
        >
          Knowledge
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/approvals"
          aria-current={current('/dashboard/approvals')}
        >
          Approvals
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/notifications"
          aria-current={current('/dashboard/notifications')}
        >
          Notifications
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/codex"
          aria-current={current('/dashboard/codex')}
        >
          Codex
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/email"
          aria-current={current('/dashboard/email')}
        >
          Email
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/crm"
          aria-current={current('/dashboard/crm')}
        >
          Clients
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/marketing"
          aria-current={current('/dashboard/marketing')}
        >
          Marketing
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/integrations"
          aria-current={current('/dashboard/integrations')}
        >
          Integrations
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/settings"
          aria-current={current('/dashboard/settings')}
        >
          Settings
        </Link>
        <Link
          className="nav-link"
          href="/dashboard/subscription"
          aria-current={current('/dashboard/subscription')}
        >
          Subscription
        </Link>
        {user.is_superuser && (
          <Link
            className="nav-link"
            href="/dashboard/platform-admin"
            aria-current={current('/dashboard/platform-admin')}
          >
            Platform admin
          </Link>
        )}
        <span className="nav-user">
          {user.full_name} · {user.email}
        </span>
      </div>
      <button className="secondary-button" type="button" onClick={handleLogout}>
        Log out
      </button>
    </header>
  );
}
