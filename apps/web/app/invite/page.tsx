'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';

import {
  acceptWorkspaceInvitation,
  AuthClientError,
  getCurrentUser,
} from '../../lib/auth-client';
import type { User } from '../../lib/auth-types';
import { KikoLogo } from '../../components/kiko/kiko-logo';

function InviteContent() {
  const token = useSearchParams().get('token') ?? '';
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [message, setMessage] = useState('');
  const [accepted, setAccepted] = useState(false);
  const returnPath = `/invite?token=${encodeURIComponent(token)}`;

  useEffect(() => {
    void getCurrentUser()
      .then(setUser)
      .finally(() => setChecking(false));
  }, []);

  async function accept() {
    setMessage('');
    try {
      await acceptWorkspaceInvitation(token);
      setAccepted(true);
      setMessage('Convite aceite. O teu workspace está pronto.');
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Não foi possível aceitar este convite.',
      );
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="invite-title">
        <KikoLogo />
        <p className="eyebrow">Convite para workspace</p>
        <h1 id="invite-title" className="auth-title">
          Junta-te à tua equipa no Kiko
        </h1>
        {!token ? (
          <p className="form-message" role="alert">
            Este link de convite está incompleto.
          </p>
        ) : checking ? (
          <p className="auth-intro">A verificar a sessão segura…</p>
        ) : user ? (
          <>
            <p className="auth-intro">Signed in as {user.email}.</p>
            {!accepted && (
              <button
                className="primary-button"
                type="button"
                onClick={() => void accept()}
              >
                Aceitar convite
              </button>
            )}
            {message && (
              <p className="form-message" role="status">
                {message}
              </p>
            )}
            {accepted && (
              <p className="auth-switch">
                <Link href="/dashboard/knowledge">Abrir workspace</Link>
              </p>
            )}
          </>
        ) : (
          <>
            <p className="auth-intro">
              Entra com o email convidado, ou cria e verifica primeiro essa
              conta.
            </p>
            <p className="auth-switch">
              <Link href={`/login?next=${encodeURIComponent(returnPath)}`}>
                Entra para aceitar
              </Link>
            </p>
            <p className="auth-switch">
              <Link href="/register">Criar uma conta</Link>
            </p>
          </>
        )}
      </section>
    </main>
  );
}

export default function InvitePage() {
  return (
    <Suspense
      fallback={<main className="loading-page">A carregar o convite…</main>}
    >
      <InviteContent />
    </Suspense>
  );
}
