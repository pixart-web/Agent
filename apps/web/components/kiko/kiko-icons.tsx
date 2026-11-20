import React from 'react';

/** Line icons drawn for Kiko (24×24, current colour). Decorative: labels carry meaning. */
const PATHS: Record<string, string> = {
  home: 'M4 11.5 12 5l8 6.5V19a1 1 0 0 1-1 1h-4.5v-5h-5v5H5a1 1 0 0 1-1-1z',
  chat: 'M5 6h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1h-7l-4 3.5V16H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1z',
  commands: 'M5 7h14M5 12h9M5 17h11',
  projects:
    'M4 7a1 1 0 0 1 1-1h4l2 2h8a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z',
  tasks:
    'M6 5h12a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zM9 12.5l2 2 4-4.5',
  agents:
    'M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM3.5 19c.6-3 2.8-4.5 5.5-4.5s4.9 1.5 5.5 4.5M16 6.2a2.6 2.6 0 0 1 0 4.8M17.5 14.6c1.6.6 2.6 2 3 4.4',
  automations: 'M13 3 5 13.5h6L10 21l8-10.5h-6z',
  crm: 'M12 12a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM5 20c.8-3.6 3.6-5.5 7-5.5s6.2 1.9 7 5.5',
  knowledge:
    'M5 5.5A1.5 1.5 0 0 1 6.5 4H19v14H6.5A1.5 1.5 0 0 0 5 19.5zM5 19.5A1.5 1.5 0 0 0 6.5 21H19M9 8h6',
  reports: 'M5 20V10M10 20V5M15 20v-7M20 20V8',
  approvals:
    'M12 3 5 6v5.5c0 4.2 2.9 7.6 7 9.5 4.1-1.9 7-5.3 7-9.5V6zM9 12l2 2 4-4.5',
  executions: 'M5 12a7 7 0 1 0 2-4.9M5 4v4h4M12 8.5V12l2.5 2',
  bell: 'M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15zM10 20.5a2.2 2.2 0 0 0 4 0',
  email:
    'M4 6.5A1.5 1.5 0 0 1 5.5 5h13A1.5 1.5 0 0 1 20 6.5v11a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5zM4.5 6.5 12 13l7.5-6.5',
  calendar:
    'M5 6.5A1.5 1.5 0 0 1 6.5 5h11A1.5 1.5 0 0 1 19 6.5v12a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 5 18.5zM5 10h14M9 3.5v3M15 3.5v3',
  marketing: 'M4 10v4h3l7 4V6l-7 4zM17 9.5a3.5 3.5 0 0 1 0 5',
  integrations: 'M9 7V4M15 7V4M7 7h10v4a5 5 0 0 1-10 0zM12 16v4',
  code: 'M9 8 5 12l4 4M15 8l4 4-4 4',
  billing:
    'M4 7.5A1.5 1.5 0 0 1 5.5 6h13A1.5 1.5 0 0 1 20 7.5v9a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 16.5zM4 10.5h16M7.5 15h3',
  admin:
    'M12 3 5 6v5.5c0 4.2 2.9 7.6 7 9.5 4.1-1.9 7-5.3 7-9.5V6zM12 9v4M12 16h.01',
  settings:
    'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3.9a7 7 0 0 0-2.1-1.2L14 3h-4l-.5 2.6a7 7 0 0 0-2.1 1.2l-2.3-.9-2 3.4 2 1.5A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.4 2.3-.9a7 7 0 0 0 2.1 1.2L10 21h4l.5-2.6a7 7 0 0 0 2.1-1.2l2.3.9 2-3.4-2-1.5c.1-.4.1-.8.1-1.2z',
  search: 'M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13zM15.5 15.5 20 20',
  send: 'M5 12h13M13 6.5 18.5 12 13 17.5',
  plan: 'M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 12h.01',
  layers:
    'M12 4 3.5 8.5 12 13l8.5-4.5zM3.5 12.5 12 17l8.5-4.5M3.5 16.5 12 21l8.5-4.5',
  chevron: 'M10 7l5 5-5 5',
  collapse: 'M15 6l-6 6 6 6',
  panel:
    'M4 6.5A1.5 1.5 0 0 1 5.5 5h13A1.5 1.5 0 0 1 20 6.5v11a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5zM15 5v14',
  logout:
    'M14 5H6.5A1.5 1.5 0 0 0 5 6.5v11A1.5 1.5 0 0 0 6.5 19H14M10 12h10M16.5 8.5 20 12l-3.5 3.5',
  link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1',
  check: 'M5 12.5 10 17 19 7',
  alert: 'M12 4 3 20h18zM12 10v4.5M12 17.5h.01',
  spark:
    'M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18',
};

export type KikoIconName = keyof typeof PATHS;

export function KikoIcon({
  name,
  size = 20,
  className,
}: {
  name: KikoIconName;
  size?: number;
  className?: string;
}) {
  return (
    <svg
      className={className ? `kiko-icon ${className}` : 'kiko-icon'}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
