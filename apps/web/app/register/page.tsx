'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { AuthClientError, register } from '../../lib/auth-client';
import { validateRegisterForm } from '../../lib/form-validation';
import { KikoLogo } from '../../components/kiko/kiko-logo';

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
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
      termsAccepted,
      privacyAccepted,
    });
    setErrors(validationErrors);
    setMessage('');
    if (Object.keys(validationErrors).length > 0) return;

    setLoading(true);
    try {
      await register(
        fullName.trim(),
        email.trim(),
        password,
        termsAccepted,
        privacyAccepted,
      );
      router.replace(`/verify-email?email=${encodeURIComponent(email.trim())}`);
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Não foi possível criar a conta agora.',
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="register-title">
        <KikoLogo />
        <p className="eyebrow">PIXART Ecosystem</p>
        <h1 id="register-title" className="auth-title">
          Cria a tua conta
        </h1>
        <p className="auth-intro">Começa uma sessão segura no Kiko.</p>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <label>
            Nome completo
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
            Palavra-passe
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
            Confirmar palavra-passe
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

          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={termsAccepted}
              onChange={(event) => setTermsAccepted(event.target.checked)}
            />
            <span>Aceito os Termos de Serviço.</span>
          </label>
          {errors.termsAccepted && (
            <span className="field-error">{errors.termsAccepted}</span>
          )}

          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={privacyAccepted}
              onChange={(event) => setPrivacyAccepted(event.target.checked)}
            />
            <span>Aceito a Política de Privacidade.</span>
          </label>
          {errors.privacyAccepted && (
            <span className="field-error">{errors.privacyAccepted}</span>
          )}

          {message && (
            <p className="form-message" role="alert">
              {message}
            </p>
          )}

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? 'A criar a conta…' : 'Criar conta'}
          </button>
        </form>

        <p className="auth-switch">
          Já tens conta? <Link href="/login">Entrar</Link>
        </p>
      </section>
    </main>
  );
}
