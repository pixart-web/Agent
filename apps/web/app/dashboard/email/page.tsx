'use client';

import type { EmailAccount, EmailMessageSummary } from '@agent/shared';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  listEmailAccounts,
  listEmailMessages,
} from '../../../lib/workflow-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';

export default function EmailInboxPage() {
  const { user, loading } = useAuthenticatedUser();
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [accountId, setAccountId] = useState('');
  const [messages, setMessages] = useState<EmailMessageSummary[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    void listEmailAccounts().then((values) => {
      setAccounts(values.filter((value) => value.status === 'connected'));
      if (values[0]) setAccountId(values[0].id);
    });
  }, [user]);

  useEffect(() => {
    if (!accountId) return;
    void listEmailMessages(accountId)
      .then((value) => setMessages(value.messages))
      .catch(() => setError('Não foi possível ler esta caixa de correio.'));
  }, [accountId]);

  if (loading || !user)
    return <main className="loading-page">Loading inbox&</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Conteúdo externo não verificado</p>
          <h1>Caixa de entrada</h1>
          <p>
            As mensagens são lidas a pedido. Os anexos nunca são descarregados
            nem executados automaticamente.
          </p>
        </div>
        <select
          aria-label="Conta de email"
          value={accountId}
          onChange={(event) => setAccountId(event.target.value)}
        >
          {accounts.map((account) => (
            <option value={account.id} key={account.id}>
              {account.email_address}
            </option>
          ))}
        </select>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <section className="workflow-panel">
        {messages.map((message) => (
          <Link
            className="agent-card agent-card--link"
            href={
              '/dashboard/email/' +
              encodeURIComponent(message.id) +
              '?account=' +
              accountId
            }
            key={message.id}
          >
            <p className="eyebrow">{message.unread ? 'Unread' : 'Read'}</p>
            <h3>{message.subject}</h3>
            <p>From: {message.sender.name || message.sender.address}</p>
            <p>{message.snippet}</p>
          </Link>
        ))}
        {messages.length === 0 && (
          <p className="empty-state">Sem mensagens para mostrar.</p>
        )}
      </section>
    </main>
  );
}
