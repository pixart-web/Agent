'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { FormEvent, Suspense, useState } from 'react';

import { AuthClientError, confirmPasswordReset } from '../../lib/auth-client';
import { KikoLogo } from '../../components/kiko/kiko-logo';

function ResetContent() {
  const token = useSearchParams().get('token') ?? '';
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token) return setMessage('Este link de reposição está incompleto.');
    if (password !== confirmPassword)
      return setMessage('As palavras-passe não coincidem.');
    setBusy(true);
    try {
      await confirmPasswordReset(token, password);
      setMessage(
        'Palavra-passe alterada. Todas as sessões abertas foram terminadas.',
      );
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Não foi possível repor a palavra-passe.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="reset-title">
        <KikoLogo />
        <p className="eyebrow">Recuperação de conta</p>
        <h1 id="reset-title" className="auth-title">
          Escolhe uma nova palavra-passe
        </h1>
        <form className="auth-form" onSubmit={submit}>
          <label>
            Nova palavra-passe
            <input
              type="password"
              autoComplete="new-password"
              minLength={10}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <label>
            Confirmar palavra-passe
            <input
              type="password"
              autoComplete="new-password"
              minLength={10}
              required
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
            />
          </label>
          {message && <p role="status">{message}</p>}
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? 'A guardar…' : 'Guardar nova palavra-passe'}
          </button>
        </form>
        <p className="auth-switch">
          <Link href="/login">Voltar a entrar</Link>
        </p>
      </section>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<main className="loading-page">A carregar…</main>}>
      <ResetContent />
    </Suspense>
  );
}
