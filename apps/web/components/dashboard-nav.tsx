'use client';

import type { Workspace } from '@agent/shared';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import React, { useEffect, useState } from 'react';

import { logout } from '../lib/auth-client';
import type { User } from '../lib/auth-types';
import { deriveKikoState } from '../lib/kiko-state';
import { listWorkspaces } from '../lib/knowledge-client';
import { isDesktop } from '../lib/platform';
import { signalsFrom, useKikoLiveData } from '../lib/use-kiko-signals';
import { resetWorkspaceRole } from '../lib/workspace-access';
import {
  getWorkspaceSettings,
  switchWorkspace,
  type WorkspaceSettings,
} from '../lib/workspace-settings-client';
import { CommandPalette, PALETTE_EVENT } from './desktop-shell';
import { KikoAvatar } from './kiko/kiko-avatar';
import { KikoContextPanel } from './kiko/kiko-context-panel';
import { KikoIcon, type KikoIconName } from './kiko/kiko-icons';

const ROLE_LABELS: Record<WorkspaceSettings['role'], string> = {
  owner: 'Dono',
  admin: 'Administrador',
  manager: 'Gestor',
  member: 'Membro',
  viewer: 'Leitura',
};

type NavItem = { href: string; label: string; icon: KikoIconName };

export const PRIMARY_NAV: NavItem[] = [
  { href: '/dashboard', label: 'Início', icon: 'home' },
  { href: '/dashboard/kiko', label: 'Conversas', icon: 'chat' },
  { href: '/dashboard/commands', label: 'Comandos', icon: 'commands' },
  { href: '/dashboard/projects', label: 'Projetos', icon: 'projects' },
  { href: '/dashboard/tasks', label: 'Tarefas', icon: 'tasks' },
  { href: '/dashboard/agents', label: 'Agentes', icon: 'agents' },
  {
    href: '/dashboard/automations',
    label: 'Automatizações',
    icon: 'automations',
  },
  { href: '/dashboard/crm', label: 'CRM', icon: 'crm' },
  { href: '/dashboard/knowledge', label: 'Conhecimento', icon: 'knowledge' },
  { href: '/dashboard/analytics', label: 'Relatórios', icon: 'reports' },
];

export const MORE_NAV: NavItem[] = [
  { href: '/dashboard/approvals', label: 'Aprovações', icon: 'approvals' },
  { href: '/dashboard/executions', label: 'Execuções', icon: 'executions' },
  { href: '/dashboard/notifications', label: 'Notificações', icon: 'bell' },
  { href: '/dashboard/email', label: 'Email', icon: 'email' },
  { href: '/dashboard/calendar', label: 'Calendário', icon: 'calendar' },
  { href: '/dashboard/marketing', label: 'Marketing', icon: 'marketing' },
  {
    href: '/dashboard/integrations',
    label: 'Integrações',
    icon: 'integrations',
  },
  { href: '/dashboard/codex', label: 'Codex', icon: 'code' },
  { href: '/dashboard/subscription', label: 'Subscrição', icon: 'billing' },
];

const COLLAPSE_KEY = 'kiko.rail.collapsed';

export function isCurrent(pathname: string, href: string): boolean {
  const path = pathname.replace(/\/$/, '') || '/';
  return href === '/dashboard'
    ? path === '/dashboard'
    : path === href || path.startsWith(`${href}/`);
}

function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(COLLAPSE_KEY) === '1';
  } catch {
    return false;
  }
}

function NavLink({
  item,
  pathname,
  onNavigate,
}: {
  item: NavItem;
  pathname: string;
  onNavigate: () => void;
}) {
  const current = isCurrent(pathname, item.href);
  return (
    <li>
      <Link
        className="kiko-rail__link"
        href={item.href}
        aria-current={current ? 'page' : undefined}
        title={item.label}
        onClick={onNavigate}
      >
        <KikoIcon name={item.icon} />
        <span className="kiko-rail__label">{item.label}</span>
      </Link>
    </li>
  );
}

/**
 * Kiko Alive application shell: navigation rail, top bar (search, activity panel) and the
 * contextual panel. Every dashboard page renders it first inside `<main>`; it keeps the
 * `DashboardNav` name so existing pages pick it up unchanged.
 */
export function DashboardNav({ user }: { user: User }) {
  const router = useRouter();
  const pathname = usePathname() ?? '';
  const live = useKikoLiveData();
  const state = deriveKikoState(signalsFrom(live));
  const [workspace, setWorkspace] = useState<Pick<
    WorkspaceSettings,
    'id' | 'name' | 'role'
  > | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const home = isCurrent(pathname, '/dashboard');

  useEffect(() => {
    setCollapsed(readCollapsed());
    let active = true;
    getWorkspaceSettings()
      .then((value) => {
        if (active)
          setWorkspace({ id: value.id, name: value.name, role: value.role });
      })
      .catch(() => undefined);
    listWorkspaces()
      .then((items) => {
        if (active) setWorkspaces(items);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  // ⌘K / Ctrl+K opens search in the browser; the macOS app sends it from its menu.
  useEffect(() => {
    if (isDesktop) return;
    function handleKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      }
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []);

  function toggleCollapsed() {
    setCollapsed((value) => {
      try {
        window.localStorage.setItem(COLLAPSE_KEY, value ? '0' : '1');
      } catch {
        // Private mode: the choice lasts for this page only.
      }
      return !value;
    });
  }

  function openSearch() {
    if (isDesktop) window.dispatchEvent(new Event(PALETTE_EVENT));
    else setPaletteOpen(true);
  }

  async function handleSwitch(id: string) {
    if (!workspace || id === workspace.id) return;
    try {
      await switchWorkspace(id);
      resetWorkspaceRole();
      window.location.reload();
    } catch {
      // The selector stays on the current workspace.
    }
  }

  async function handleLogout() {
    await logout();
    router.replace('/login');
  }

  const unread = live.overview?.unread_alerts ?? 0;
  const approvals = live.overview?.pending_approvals ?? 0;
  const moreActive = MORE_NAV.some((item) => isCurrent(pathname, item.href));
  const closeMenu = () => setMenuOpen(false);

  return (
    <>
      <a className="kiko-skip-link" href="#kiko-content">
        Saltar para o conteúdo
      </a>
      <nav
        className={`kiko-rail${collapsed ? ' is-collapsed' : ''}${menuOpen ? ' is-open' : ''}`}
        aria-label="Navegação principal"
      >
        <div className="kiko-rail__brand">
          <Link
            href="/dashboard"
            className="kiko-rail__brand-link"
            onClick={closeMenu}
          >
            <KikoAvatar state={state} size={34} decorative />
            <span className="kiko-rail__brand-text">
              <strong>Kiko</strong>
              <span>AI Operating System</span>
            </span>
          </Link>
          <button
            type="button"
            className="kiko-icon-button kiko-rail__collapse"
            onClick={toggleCollapsed}
            aria-label={collapsed ? 'Expandir navegação' : 'Recolher navegação'}
            aria-pressed={collapsed}
          >
            <KikoIcon name="collapse" />
          </button>
        </div>

        <ul className="kiko-rail__list">
          {PRIMARY_NAV.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              pathname={pathname}
              onNavigate={closeMenu}
            />
          ))}
        </ul>

        <details className="kiko-rail__more" open={moreActive || undefined}>
          <summary className="kiko-rail__link">
            <KikoIcon name="layers" />
            <span className="kiko-rail__label">Mais módulos</span>
          </summary>
          <ul className="kiko-rail__list">
            {MORE_NAV.map((item) => (
              <NavLink
                key={item.href}
                item={item}
                pathname={pathname}
                onNavigate={closeMenu}
              />
            ))}
            {user.is_superuser ? (
              <NavLink
                item={{
                  href: '/dashboard/platform-admin',
                  label: 'Administração',
                  icon: 'admin',
                }}
                pathname={pathname}
                onNavigate={closeMenu}
              />
            ) : null}
          </ul>
        </details>

        <div className="kiko-rail__footer">
          {workspace ? (
            <div className="kiko-workspace">
              <span className="kiko-workspace__mark" aria-hidden="true">
                {workspace.name.slice(0, 1).toUpperCase()}
              </span>
              <span className="kiko-workspace__text">
                <span className="kiko-workspace__caption">
                  Workspace · {ROLE_LABELS[workspace.role]}
                </span>
                {workspaces.length > 1 ? (
                  <select
                    value={workspace.id}
                    onChange={(event) => void handleSwitch(event.target.value)}
                    aria-label="Mudar de workspace"
                  >
                    {workspaces.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <strong>{workspace.name}</strong>
                )}
              </span>
            </div>
          ) : null}
          <ul className="kiko-rail__list">
            <NavLink
              item={{
                href: '/dashboard/settings',
                label: 'Definições',
                icon: 'settings',
              }}
              pathname={pathname}
              onNavigate={closeMenu}
            />
          </ul>
          <div className="kiko-rail__user">
            <span className="kiko-rail__user-text">
              <strong>{user.full_name}</strong>
              <span>{user.email}</span>
            </span>
            <button
              type="button"
              className="kiko-rail__logout"
              onClick={handleLogout}
              title="Terminar sessão"
            >
              <KikoIcon name="logout" size={18} />
              <span className="kiko-rail__label">Terminar sessão</span>
            </button>
          </div>
        </div>
      </nav>

      <div className="kiko-topbar">
        <button
          type="button"
          className="kiko-icon-button kiko-topbar__menu"
          onClick={() => setMenuOpen((open) => !open)}
          aria-label="Abrir navegação"
          aria-expanded={menuOpen}
        >
          <KikoIcon name="commands" />
        </button>
        <button type="button" className="kiko-search" onClick={openSearch}>
          <KikoIcon name="search" size={18} />
          <span>Pesquisar no Kiko…</span>
          <kbd aria-hidden="true">⌘ K</kbd>
        </button>
        {!home ? (
          <button
            type="button"
            className="kiko-icon-button kiko-topbar__activity"
            onClick={() => setPanelOpen((open) => !open)}
            aria-expanded={panelOpen}
            aria-controls="kiko-context-panel"
            aria-label={
              unread + approvals > 0
                ? `Atividade: ${approvals} aprovações pendentes, ${unread} alertas por ler`
                : 'Atividade'
            }
          >
            <KikoIcon name="bell" />
            {unread + approvals > 0 ? (
              <span className="kiko-badge" aria-hidden="true">
                {Math.min(unread + approvals, 99)}
              </span>
            ) : null}
          </button>
        ) : null}
      </div>

      {menuOpen ? (
        <button
          type="button"
          className="kiko-scrim"
          aria-label="Fechar navegação"
          onClick={closeMenu}
        />
      ) : null}

      {!home && panelOpen ? (
        <KikoContextPanel
          id="kiko-context-panel"
          live={live}
          variant="drawer"
          onClose={() => setPanelOpen(false)}
        />
      ) : null}

      {paletteOpen ? (
        <CommandPalette onClose={() => setPaletteOpen(false)} />
      ) : null}

      <span id="kiko-content" className="kiko-content-anchor" tabIndex={-1} />

      {workspace?.role === 'viewer' && (
        <p className="workspace-access-notice" role="status">
          Tens acesso só de leitura a {workspace.name}. Podes ver tudo, mas para
          criar ou alterar é preciso que um dono ou administrador te dê acesso
          de edição.
        </p>
      )}
    </>
  );
}
