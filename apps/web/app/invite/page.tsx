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
      setMessage('Invitation accepted. Your workspace is ready.');
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Unable to accept this invitation.',
      );
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="invite-title">
        <p className="eyebrow">Workspace invitation</p>
        <h1 id="invite-title" className="auth-title">Join your team on Kiko</h1>
        {!token ? (
          <p className="form-message" role="alert">This invitation link is incomplete.</p>
        ) : checking ? (
          <p className="auth-intro">Checking your secure session…</p>
        ) : user ? (
          <>
            <p className="auth-intro">Signed in as {user.email}.</p>
            {!accepted && <button className="primary-button" type="button" onClick={() => void accept()}>Accept invitation</button>}
            {message && <p className="form-message" role="status">{message}</p>}
            {accepted && <p className="auth-switch"><Link href="/dashboard/knowledge">Open workspace</Link></p>}
          </>
        ) : (
          <>
            <p className="auth-intro">Sign in with the invited email address, or create and verify that account first.</p>
            <p className="auth-switch"><Link href={`/login?next=${encodeURIComponent(returnPath)}`}>Sign in to accept</Link></p>
            <p className="auth-switch"><Link href="/register">Create an account</Link></p>
          </>
        )}
      </section>
    </main>
  );
}

export default function InvitePage() {
  return <Suspense fallback={<main className="loading-page">Loading invitation…</main>}><InviteContent /></Suspense>;
}
