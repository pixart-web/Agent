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
      .catch(() => setError('Unable to read this mailbox.'));
  }, [accountId]);

  if (loading || !user)
    return <main className="loading-page">Loading inbox&</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Untrusted external content</p>
          <h1>Email inbox</h1>
          <p>
            Messages are read on demand. Attachments are never downloaded or
            executed automatically.
          </p>
        </div>
        <select
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
          <p className="empty-state">No messages to show.</p>
        )}
      </section>
    </main>
  );
}
