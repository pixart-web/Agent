'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { FormEvent, Suspense, useEffect, useState } from 'react';

import {
  AuthClientError,
  resendVerification,
  verifyEmail,
} from '../../lib/auth-client';
import { KikoLogo } from '../../components/kiko/kiko-logo';

function VerificationContent() {
  const search = useSearchParams();
  const token = search.get('token');
  const initialEmail = search.get('email') ?? '';
  const [email, setEmail] = useState(initialEmail);
  const [message, setMessage] = useState(
    token
      ? 'A verificar o teu email…'
      : 'Procura na tua caixa de correio o link de verificação.',
  );
  const [busy, setBusy] = useState(Boolean(token));

  useEffect(() => {
    if (!token) return;
    void verifyEmail(token)
      .then(() => setMessage('Email verificado. Já podes entrar.'))
      .catch((error) =>
        setMessage(
          error instanceof AuthClientError
            ? error.message
            : 'Não foi possível verificar este email.',
        ),
      )
      .finally(() => setBusy(false));
  }, [token]);

  async function resend(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await resendVerification(email.trim());
      setMessage(
        'Se a conta for elegível, foi enviado um novo email de verificação.',
      );
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Não foi possível pedir outro email.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="verify-title">
        <KikoLogo />
        <p className="eyebrow">Identidade segura</p>
        <h1 id="verify-title" className="auth-title">
          Verifica o teu email
        </h1>
        <p className="auth-intro" role="status">
          {message}
        </p>
        {!token && (
          <form className="auth-form" onSubmit={resend}>
            <label>
              Email
              <input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <button className="primary-button" type="submit" disabled={busy}>
              {busy ? 'A pedir…' : 'Reenviar email de verificação'}
            </button>
          </form>
        )}
        <p className="auth-switch">
          <Link href="/login">Voltar a entrar</Link>
        </p>
      </section>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<main className="loading-page">A carregar…</main>}>
      <VerificationContent />
    </Suspense>
  );
}
