'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useEffect, useState } from 'react';

import {
  getAppInfo,
  setServerUrl,
  type DesktopAppInfo,
} from '../../../lib/desktop-bridge';
import { isDesktop } from '../../../lib/platform';
import { KikoLogo } from '../../../components/kiko/kiko-logo';

/** Desktop-only: choose which Kiko server this app talks to. */
export default function DesktopConnectionPage() {
  const router = useRouter();
  const [info, setInfo] = useState<DesktopAppInfo | null>(null);
  const [value, setValue] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isDesktop) {
      router.replace('/');
      return;
    }
    void getAppInfo().then((current) => {
      setInfo(current);
      setValue(current.apiBaseUrl);
    });
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      await setServerUrl(value);
      router.replace('/desktop/');
    } catch (failure) {
      setError(
        typeof failure === 'string'
          ? failure
          : 'This server address cannot be used.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="connection-title">
        <KikoLogo />
        <p className="eyebrow">
          Kiko for macOS{info ? ` · ${info.version}` : ''}
        </p>
        <h1 id="connection-title" className="auth-title">
          Server connection
        </h1>
        <p className="auth-intro">
          Kiko runs your business data, agents and approvals on the Kiko server.
          Enter the HTTPS address your administrator gave you.
        </p>
        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <label>
            Server address
            <input
              type="url"
              inputMode="url"
              autoComplete="url"
              spellCheck={false}
              required
              value={value}
              onChange={(event) => setValue(event.target.value)}
              placeholder="https://kiko.example.com"
              aria-describedby="connection-hint connection-error"
            />
          </label>
          <p id="connection-hint" className="form-hint">
            HTTPS is required. Plain HTTP is accepted only for a server on this
            Mac (localhost).
          </p>
          {error ? (
            <p id="connection-error" className="field-error" role="alert">
              {error}
            </p>
          ) : null}
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? 'Saving…' : 'Save and connect'}
          </button>
          <Link className="secondary-button" href="/desktop/">
            Cancel
          </Link>
        </form>
      </section>
    </main>
  );
}
