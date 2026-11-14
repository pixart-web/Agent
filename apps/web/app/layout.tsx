import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import { DesktopShell } from '../components/desktop-shell';
import { KIKO_PLATFORM, isDesktop } from '../lib/platform';
import './globals.css';

export const metadata: Metadata = {
  title: 'Kiko | Pixart AI Operating System',
  description:
    'Kiko coordinates safe, auditable multi-agent operations for Pixart.',
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" data-platform={KIKO_PLATFORM}>
      <body>
        {children}
        {isDesktop ? <DesktopShell /> : null}
      </body>
    </html>
  );
}
