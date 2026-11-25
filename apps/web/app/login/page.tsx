'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { AuthClientError, login } from '../../lib/auth-client';
import { validateLoginForm } from '../../lib/form-validation';
import { KikoLogo } from '../../components/kiko/kiko-logo';

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
      const requested = new URLSearchParams(window.location.search).get('next');
      const destination =
        requested?.startsWith('/') && !requested.startsWith('//')
          ? requested
          : '/dashboard';
      router.replace(destination);
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Não foi possível entrar agora.',
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="login-title">
        <KikoLogo />
        <p className="eyebrow">PIXART Ecosystem</p>
        <h1 id="login-title" className="auth-title">
          Entrar no Kiko
        </h1>
        <p className="auth-intro">
          Continua para o sistema operativo de IA da Pixart.
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
            Palavra-passe
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
            {loading ? 'A entrar…' : 'Entrar'}
          </button>
        </form>

        <p className="auth-switch">
          Ainda não tens conta? <Link href="/register">Criar uma conta</Link>
        </p>
        <p className="auth-switch">
          <Link href="/forgot-password">Esqueceste-te da palavra-passe?</Link>
        </p>
      </section>
    </main>
  );
}
