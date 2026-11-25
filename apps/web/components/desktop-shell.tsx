'use client';

import { usePathname, useRouter } from 'next/navigation';
import {
  KeyboardEvent as ReactKeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { apiFetch } from '../lib/auth-client';
import {
  CONNECTIVITY_EVENT,
  notify,
  onCommand,
  onNavigate,
  openExternal,
  takePendingRoute,
} from '../lib/desktop-bridge';
import { rememberRoute } from '../lib/desktop-routes';
import { listNotifications } from '../lib/notification-client';
import { serverText } from '../lib/labels';

const NOTIFICATION_POLL_MS = 60_000;

export const PALETTE_DESTINATIONS: {
  label: string;
  route: string;
  keywords: string;
}[] = [
  { label: 'Início', route: '/dashboard/', keywords: 'overview dashboard' },
  {
    label: 'Conversas com o Kiko',
    route: '/dashboard/kiko/',
    keywords: 'chat conversation ask',
  },
  {
    label: 'Novo comando',
    route: '/dashboard/commands/new/',
    keywords: 'create request',
  },
  {
    label: 'Comandos',
    route: '/dashboard/commands/',
    keywords: 'requests plans',
  },
  { label: 'Tarefas', route: '/dashboard/tasks/', keywords: 'work board' },
  { label: 'Projetos', route: '/dashboard/projects/', keywords: '' },
  {
    label: 'Aprovações',
    route: '/dashboard/approvals/',
    keywords: 'review governance',
  },
  {
    label: 'Execuções',
    route: '/dashboard/executions/',
    keywords: 'runs progress',
  },
  { label: 'Agentes', route: '/dashboard/agents/', keywords: 'specialists' },
  {
    label: 'CRM',
    route: '/dashboard/crm/',
    keywords: 'clients contacts organizations sales',
  },
  {
    label: 'Marketing',
    route: '/dashboard/marketing/',
    keywords: 'campaigns content',
  },
  {
    label: 'Calendário',
    route: '/dashboard/calendar/',
    keywords: 'events meetings',
  },
  { label: 'Email', route: '/dashboard/email/', keywords: 'inbox messages' },
  {
    label: 'Automatizações',
    route: '/dashboard/automations/',
    keywords: 'triggers',
  },
  {
    label: 'Conhecimento',
    route: '/dashboard/knowledge/',
    keywords: 'documents',
  },
  {
    label: 'Integrações',
    route: '/dashboard/integrations/',
    keywords: 'connections github gmail',
  },
  { label: 'Relatórios', route: '/dashboard/analytics/', keywords: 'metrics' },
  {
    label: 'Notificações',
    route: '/dashboard/notifications/',
    keywords: 'alerts',
  },
  {
    label: 'Definições',
    route: '/dashboard/settings/',
    keywords: 'team workspace profile',
  },
  {
    label: 'Subscrição',
    route: '/dashboard/subscription/',
    keywords: 'plan billing',
  },
  {
    label: 'Ligação ao servidor',
    route: '/desktop/connection/',
    keywords: 'server url',
  },
];

/** Opens the command palette (the shell's search button sends it; ⌘K on macOS too). */
export const PALETTE_EVENT = 'kiko:palette';

export function filterDestinations(query: string) {
  const needle = query.trim().toLowerCase();
  if (!needle) return PALETTE_DESTINATIONS;
  return PALETTE_DESTINATIONS.filter((item) =>
    `${item.label} ${item.keywords}`.toLowerCase().includes(needle),
  );
}

/** True for links that must leave the app (opened in the default browser or mail app). */
export function isExternalHref(href: string): boolean {
  return /^(https?:|mailto:)/i.test(href);
}

export function CommandPalette({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const results = useMemo(() => filterDestinations(query), [query]);

  useEffect(() => inputRef.current?.focus(), []);
  useEffect(() => setActive(0), [query]);

  function go(route: string) {
    onClose();
    router.push(route);
  }

  function handleKey(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') onClose();
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive((value) => Math.min(value + 1, results.length - 1));
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((value) => Math.max(value - 1, 0));
    }
    if (event.key === 'Enter' && results[active]) go(results[active].route);
  }

  return (
    <div className="desktop-palette__backdrop" onMouseDown={onClose}>
      <div
        className="desktop-palette"
        role="dialog"
        aria-modal="true"
        aria-label="Pesquisar no Kiko"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <input
          ref={inputRef}
          className="desktop-palette__input"
          placeholder="Ir para…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={handleKey}
          role="combobox"
          aria-expanded="true"
          aria-controls="desktop-palette-results"
          aria-activedescendant={
            results[active] ? `palette-${active}` : undefined
          }
        />
        <ul
          id="desktop-palette-results"
          className="desktop-palette__results"
          role="listbox"
        >
          {results.map((item, index) => (
            <li
              key={item.route}
              id={`palette-${index}`}
              role="option"
              aria-selected={index === active}
              className={index === active ? 'is-active' : undefined}
              onMouseEnter={() => setActive(index)}
              onClick={() => go(item.route)}
            >
              {item.label}
            </li>
          ))}
          {results.length === 0 ? (
            <li className="desktop-palette__empty">Nenhum ecrã encontrado</li>
          ) : null}
        </ul>
      </div>
    </div>
  );
}

/**
 * Native integration layer for the macOS app. Rendered only in the desktop build.
 * It owns menu navigation, the command palette, external links, connectivity state and
 * native notifications. It never performs business writes.
 */
export function DesktopShell() {
  const router = useRouter();
  const pathname = usePathname();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [offline, setOffline] = useState(false);
  const seenNotifications = useRef<Set<string> | null>(null);

  useEffect(() => {
    if (pathname) rememberRoute(pathname);
  }, [pathname]);

  useEffect(() => {
    const navigate = (route: string) => {
      setPaletteOpen(false);
      router.push(route);
    };
    const navigation = onNavigate(navigate);
    // A link that launched the app arrived before this listener existed; open it now.
    void navigation
      .then(() => takePendingRoute())
      .then((route) => {
        if (route) navigate(route);
      })
      .catch(() => undefined);
    const unlisteners = [
      navigation,
      onCommand((command) => {
        if (command === 'back') window.history.back();
        if (command === 'forward') window.history.forward();
        if (command === 'reload') window.location.reload();
        if (command === 'palette') setPaletteOpen((open) => !open);
      }),
    ];
    return () => {
      for (const pending of unlisteners)
        void pending.then((unlisten) => unlisten());
    };
  }, [router]);

  useEffect(() => {
    function handleConnectivity(event: Event) {
      setOffline(!(event as CustomEvent<{ online: boolean }>).detail.online);
    }
    function handleClick(event: MouseEvent) {
      const anchor = (event.target as HTMLElement | null)?.closest('a');
      const href = anchor?.getAttribute('href');
      if (!anchor || !href || !isExternalHref(href)) return;
      event.preventDefault();
      void openExternal(anchor.href);
    }
    const openPalette = () => setPaletteOpen(true);
    window.addEventListener(CONNECTIVITY_EVENT, handleConnectivity);
    window.addEventListener(PALETTE_EVENT, openPalette);
    document.addEventListener('click', handleClick, true);
    return () => {
      window.removeEventListener(PALETTE_EVENT, openPalette);
      window.removeEventListener(CONNECTIVITY_EVENT, handleConnectivity);
      document.removeEventListener('click', handleClick, true);
    };
  }, []);

  const pollNotifications = useCallback(async () => {
    if (!pathname?.startsWith('/dashboard')) return;
    try {
      const { notifications } = await listNotifications();
      const unread = notifications.filter((item) => !item.read_at);
      if (seenNotifications.current === null) {
        // First poll after launch: existing notifications are not re-announced.
        seenNotifications.current = new Set(
          notifications.map((item) => item.id),
        );
        return;
      }
      for (const item of unread) {
        if (seenNotifications.current.has(item.id)) continue;
        seenNotifications.current.add(item.id);
        void notify(serverText(item.title), item.body);
      }
    } catch {
      // Signed out or offline: the connectivity banner and auth redirects handle it.
    }
  }, [pathname]);

  useEffect(() => {
    void pollNotifications();
    const timer = window.setInterval(
      () => void pollNotifications(),
      NOTIFICATION_POLL_MS,
    );
    return () => window.clearInterval(timer);
  }, [pollNotifications]);

  async function retryConnection() {
    try {
      const response = await apiFetch('/health');
      setOffline(!response.ok);
    } catch {
      setOffline(true);
    }
  }

  return (
    <>
      <div
        className="desktop-titlebar"
        data-tauri-drag-region
        aria-hidden="true"
      />
      {offline ? (
        <div className="desktop-offline" role="status">
          <span>
            Kiko can’t reach the server. Changes can’t be saved until the
            connection returns.
          </span>
          <button
            type="button"
            className="secondary-button"
            onClick={retryConnection}
          >
            Retry
          </button>
        </div>
      ) : null}
      {paletteOpen ? (
        <CommandPalette onClose={() => setPaletteOpen(false)} />
      ) : null}
    </>
  );
}
