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
          : 'Este endereço de servidor não pode ser usado.',
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
          Ligação ao servidor
        </h1>
        <p className="auth-intro">
          O Kiko guarda os dados do negócio, os agentes e as aprovações no
          servidor Kiko. Indica o endereço HTTPS que o administrador te deu.
        </p>
        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <label>
            Endereço do servidor
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
            É obrigatório HTTPS. HTTP simples só é aceite para um servidor neste
            Mac (localhost).
          </p>
          {error ? (
            <p id="connection-error" className="field-error" role="alert">
              {error}
            </p>
          ) : null}
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? 'A guardar…' : 'Guardar e ligar'}
          </button>
          <Link className="secondary-button" href="/desktop/">
            Cancelar
          </Link>
        </form>
      </section>
    </main>
  );
}
