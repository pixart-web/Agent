'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { AuthClientError, register } from '../../lib/auth-client';
import { validateRegisterForm } from '../../lib/form-validation';

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationErrors = validateRegisterForm({
      fullName,
      email,
      password,
      confirmPassword,
    });
    setErrors(validationErrors);
    setMessage('');
    if (Object.keys(validationErrors).length > 0) return;

    setLoading(true);
    try {
      await register(fullName.trim(), email.trim(), password);
      router.replace('/dashboard');
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Unable to create the account right now.',
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="register-title">
        <p className="eyebrow">Pixart operations</p>
        <h1 id="register-title" className="auth-title">
          Create your account
        </h1>
        <p className="auth-intro">Start a secure Agent session.</p>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <label>
            Full name
            <input
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
            />
          </label>
          {errors.fullName && (
            <span className="field-error">{errors.fullName}</span>
          )}

          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          {errors.email && <span className="field-error">{errors.email}</span>}

          <label>
            Password
            <input
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {errors.password && (
            <span className="field-error">{errors.password}</span>
          )}

          <label>
            Confirm password
            <input
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
            />
          </label>
          {errors.confirmPassword && (
            <span className="field-error">{errors.confirmPassword}</span>
          )}

          {message && (
            <p className="form-message" role="alert">
              {message}
            </p>
          )}

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="auth-switch">
          Already registered? <Link href="/login">Sign in</Link>
        </p>
      </section>
    </main>
  );
}
