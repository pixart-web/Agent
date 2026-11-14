'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { FormEvent, Suspense, useEffect, useState } from 'react';

import {
  AuthClientError,
  resendVerification,
  verifyEmail,
} from '../../lib/auth-client';

function VerificationContent() {
  const search = useSearchParams();
  const token = search.get('token');
  const initialEmail = search.get('email') ?? '';
  const [email, setEmail] = useState(initialEmail);
  const [message, setMessage] = useState(
    token
      ? 'Verifying your email…'
      : 'Check your inbox for a verification link.',
  );
  const [busy, setBusy] = useState(Boolean(token));

  useEffect(() => {
    if (!token) return;
    void verifyEmail(token)
      .then(() => setMessage('Email verified. You can now sign in.'))
      .catch((error) =>
        setMessage(
          error instanceof AuthClientError
            ? error.message
            : 'Unable to verify this email.',
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
        'If the account is eligible, a new verification email was queued.',
      );
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Unable to request another email.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="verify-title">
        <p className="eyebrow">Secure identity</p>
        <h1 id="verify-title" className="auth-title">
          Verify your email
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
              {busy ? 'Requesting…' : 'Resend verification email'}
            </button>
          </form>
        )}
        <p className="auth-switch">
          <Link href="/login">Return to sign in</Link>
        </p>
      </section>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<main className="loading-page">Loading…</main>}>
      <VerificationContent />
    </Suspense>
  );
}
