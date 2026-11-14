'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';

import { AuthClientError, requestPasswordReset } from '../../lib/auth-client';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await requestPasswordReset(email.trim());
      setMessage('If the account is eligible, a reset email was queued.');
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Unable to request a password reset.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="forgot-title">
        <p className="eyebrow">Account recovery</p>
        <h1 id="forgot-title" className="auth-title">
          Reset your password
        </h1>
        <p className="auth-intro">
          Enter your account email. The response is identical whether an account
          exists or not.
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
            {busy ? 'Requesting…' : 'Request reset'}
          </button>
        </form>
        <p className="auth-switch">
          <Link href="/login">Return to sign in</Link>
        </p>
      </section>
    </main>
  );
}
