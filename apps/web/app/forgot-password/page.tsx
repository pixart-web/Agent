'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';

import { AuthClientError, requestPasswordReset } from '../../lib/auth-client';
import { KikoLogo } from '../../components/kiko/kiko-logo';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await requestPasswordReset(email.trim());
      setMessage(
        'Se a conta for elegível, foi enviado um email para repor a palavra-passe.',
      );
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Não foi possível pedir a reposição da palavra-passe.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="forgot-title">
        <KikoLogo />
        <p className="eyebrow">Recuperação de conta</p>
        <h1 id="forgot-title" className="auth-title">
          Repõe a tua palavra-passe
        </h1>
        <p className="auth-intro">
          Indica o email da tua conta. A resposta é a mesma quer a conta exista
          ou não.
        </p>
        <form className="auth-form" onSubmit={submit}>
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
          {message && <p role="status">{message}</p>}
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? 'A pedir…' : 'Pedir reposição'}
          </button>
        </form>
        <p className="auth-switch">
          <Link href="/login">Voltar a entrar</Link>
        </p>
      </section>
    </main>
  );
}
