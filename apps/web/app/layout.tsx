import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import { DesktopShell } from '../components/desktop-shell';
import { KIKO_PLATFORM, isDesktop } from '../lib/platform';
import './globals.css';
import './kiko-alive.css';

export const metadata: Metadata = {
  title: 'Kiko | Sistema operativo de IA da Pixart',
  description:
    'O Kiko transforma pedidos em planos, coordena agentes especializados e pede aprovação antes de ações sensíveis.',
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="pt-PT" data-platform={KIKO_PLATFORM}>
      <body>
        {children}
        {isDesktop ? <DesktopShell /> : null}
      </body>
    </html>
  );
}
