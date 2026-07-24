'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { AuthClientError, login } from '../../lib/auth-client';
import { validateLoginForm } from '../../lib/form-validation';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationErrors = validateLoginForm({ email, password });
    setErrors(validationErrors);
    setMessage('');
    if (Object.keys(validationErrors).length > 0) return;

    setLoading(true);
    try {
      await login(email.trim(), password);
      router.replace('/dashboard');
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Unable to sign in right now.',
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="login-title">
        <p className="eyebrow">Pixart operations</p>
        <h1 id="login-title" className="auth-title">
          Sign in to Agent
        </h1>
        <p className="auth-intro">
          Continue to the Pixart AI Operating System.
        </p>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              aria-describedby={errors.email ? 'email-error' : undefined}
            />
          </label>
          {errors.email && (
            <span id="email-error" className="field-error">
              {errors.email}
            </span>
          )}

          <label>
            Password
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              aria-describedby={errors.password ? 'password-error' : undefined}
            />
          </label>
          {errors.password && (
            <span id="password-error" className="field-error">
              {errors.password}
            </span>
          )}

          {message && (
            <p className="form-message" role="alert">
              {message}
            </p>
          )}

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="auth-switch">
          New to Agent? <Link href="/register">Create an account</Link>
        </p>
      </section>
    </main>
  );
}
