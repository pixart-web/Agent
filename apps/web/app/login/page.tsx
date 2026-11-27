'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { AuthClientError, login, verifyMfa } from '../../lib/auth-client';
import { validateLoginForm } from '../../lib/form-validation';
import { KikoLogo } from '../../components/kiko/kiko-logo';

function destinationAfterLogin(): string {
  const requested = new URLSearchParams(window.location.search).get('next');
  return requested?.startsWith('/') && !requested.startsWith('//')
    ? requested
    : '/dashboard';
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [code, setCode] = useState('');

  function failure(error: unknown, fallback: string) {
    setMessage(error instanceof AuthClientError ? error.message : fallback);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationErrors = validateLoginForm({ email, password });
    setErrors(validationErrors);
    setMessage('');
    if (Object.keys(validationErrors).length > 0) return;

    setLoading(true);
    try {
      const result = await login(email.trim(), password);
      if (result.mfaToken) {
        setMfaToken(result.mfaToken);
        setPassword('');
        return;
      }
      router.replace(destinationAfterLogin());
    } catch (error) {
      failure(error, 'Não foi possível entrar agora.');
    } finally {
      setLoading(false);
    }
  }

  async function handleCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage('');
    if (!mfaToken) return;
    if (code.trim().length < 6) {
      setErrors({
        code: 'Indica o código de 6 dígitos ou um código de recuperação.',
      });
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      await verifyMfa(mfaToken, code);
      router.replace(destinationAfterLogin());
    } catch (error) {
      failure(error, 'Não foi possível confirmar o código.');
      setCode('');
    } finally {
      setLoading(false);
    }
  }

  if (mfaToken) {
    return (
      <main className="auth-page">
        <section className="auth-card" aria-labelledby="mfa-title">
          <KikoLogo />
          <p className="eyebrow">Verificação em dois passos</p>
          <h1 id="mfa-title" className="auth-title">
            Confirma que és tu
          </h1>
          <p className="auth-intro">
            Abre a app de autenticação e indica o código de 6 dígitos do Kiko.
            Sem o telemóvel, usa um dos códigos de recuperação.
          </p>
          <form className="auth-form" onSubmit={handleCode} noValidate>
            <label>
              Código
              <input
                type="text"
                autoComplete="one-time-code"
                autoCapitalize="off"
                spellCheck={false}
                autoFocus
                maxLength={32}
                value={code}
                onChange={(event) => setCode(event.target.value)}
                aria-describedby={errors.code ? 'code-error' : undefined}
              />
            </label>
            {errors.code && (
              <span id="code-error" className="field-error">
                {errors.code}
              </span>
            )}
            {message && (
              <p className="form-message" role="alert">
                {message}
              </p>
            )}
            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? 'A confirmar…' : 'Confirmar'}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => {
                setMfaToken(null);
                setCode('');
                setMessage('');
              }}
            >
              Voltar
            </button>
          </form>
        </section>
      </main>
    );
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
