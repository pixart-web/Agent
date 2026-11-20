'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { getCurrentUser } from '../../lib/auth-client';
import { getAppInfo, type DesktopAppInfo } from '../../lib/desktop-bridge';
import { lastRoute } from '../../lib/desktop-routes';
import { isDesktop } from '../../lib/platform';
import { KikoLogo } from '../../components/kiko/kiko-logo';

type LaunchState =
  | { status: 'starting' }
  | { status: 'unreachable'; info: DesktopAppInfo | null; detail: string };

/** Desktop entry point: restore the session (if any) and open the last screen. */
export default function DesktopLaunchPage() {
  const router = useRouter();
  const [state, setState] = useState<LaunchState>({ status: 'starting' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!isDesktop) {
      router.replace('/');
      return;
    }
    let active = true;
    void (async () => {
      let info: DesktopAppInfo | null = null;
      try {
        info = await getAppInfo();
        const user = await getCurrentUser();
        if (!active) return;
        if (!user) {
          router.replace('/login/');
        } else if (!user.onboarding_completed_at) {
          router.replace('/onboarding/');
        } else {
          router.replace(lastRoute() ?? '/dashboard/');
        }
      } catch (error) {
        if (!active) return;
        setState({
          status: 'unreachable',
          info,
          detail:
            error instanceof Error
              ? error.message
              : 'The Kiko server could not be reached.',
        });
      }
    })();
    return () => {
      active = false;
    };
  }, [attempt, router]);

  if (state.status === 'starting') {
    return (
      <main className="loading-page" aria-live="polite">
        Opening Kiko…
      </main>
    );
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="offline-title">
        <KikoLogo />
        <p className="eyebrow">Connection</p>
        <h1 id="offline-title" className="auth-title">
          Kiko can’t reach its server
        </h1>
        <p className="auth-intro">
          {state.info ? `Server: ${state.info.apiBaseUrl}. ` : ''}
          Check your internet connection or the server address. Nothing was
          changed while offline.
        </p>
        <p className="form-hint">{state.detail}</p>
        <div className="auth-form">
          <button
            className="primary-button"
            type="button"
            onClick={() => {
              setState({ status: 'starting' });
              setAttempt((value) => value + 1);
            }}
          >
            Try again
          </button>
          <Link className="secondary-button" href="/desktop/connection/">
            Change server
          </Link>
        </div>
      </section>
    </main>
  );
}
