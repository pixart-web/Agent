'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { FormEvent, Suspense, useState } from 'react';

import { AuthClientError, confirmPasswordReset } from '../../lib/auth-client';

function ResetContent() {
  const token = useSearchParams().get('token') ?? '';
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token) return setMessage('This reset link is incomplete.');
    if (password !== confirmPassword)
      return setMessage('Passwords do not match.');
    setBusy(true);
    try {
      await confirmPasswordReset(token, password);
      setMessage('Password changed. All existing sessions were revoked.');
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Unable to reset the password.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="reset-title">
        <p className="eyebrow">Account recovery</p>
        <h1 id="reset-title" className="auth-title">
          Choose a new password
        </h1>
        <form className="auth-form" onSubmit={submit}>
          <label>
            New password
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
            Confirm password
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
            {busy ? 'Saving…' : 'Save new password'}
          </button>
        </form>
        <p className="auth-switch">
          <Link href="/login">Return to sign in</Link>
        </p>
      </section>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<main className="loading-page">Loading…</main>}>
      <ResetContent />
    </Suspense>
  );
}
