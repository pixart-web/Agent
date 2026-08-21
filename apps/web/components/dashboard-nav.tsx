'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { logout } from '../lib/auth-client';
import type { User } from '../lib/auth-types';

export function DashboardNav({ user }: { user: User }) {
  const router = useRouter();

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
        <Link className="nav-link" href="/dashboard/commands">
          Commands
        </Link>
        <Link className="nav-link" href="/dashboard/executions">
          Executions
        </Link>
        <Link className="nav-link" href="/dashboard/agents">
          Agents
        </Link>
        <Link className="nav-link" href="/dashboard/approvals">
          Approvals
        </Link>
        <Link className="nav-link" href="/dashboard/codex">
          Codex
        </Link>
        <Link className="nav-link" href="/dashboard/integrations">
          Integrations
        </Link>
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
