'use client';

import type {
  ConversationDetail,
  ConversationMessage,
  ConversationOperation,
} from '@agent/shared';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { FormEvent, useCallback, useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { ConversationOperationStatus } from '../../../../components/conversation-operation-status';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';
import {
  getConversation,
  sendConversationMessage,
  WorkflowApiError,
} from '../../../../lib/workflow-client';

export default function ConversationPage() {
  const params = useParams<{ id: string }>();
  const { user, loading } = useAuthenticatedUser();
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setDetail(await getConversation(params.id));
    } catch {
      setError('Não foi possível carregar esta conversa.');
    }
  }, [params.id]);

  useEffect(() => {
    if (!user) return;
    void load();
    const interval = window.setInterval(() => void load(), 10_000);
    return () => window.clearInterval(interval);
  }, [load, user]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = message.trim();
    if (!content) return;
    setSubmitting(true);
    setError('');
    try {
      const turn = await sendConversationMessage(params.id, content);
      setDetail((current) =>
        current
          ? {
              ...current,
              conversation: turn.conversation,
              messages: [...current.messages, ...turn.messages],
              operations: [
                ...current.operations,
                {
                  command: turn.command,
                  plan: null,
                  supervisor_status: null,
                  task_counts: {},
                  pending_approvals: 0,
                  latest_error: null,
                },
              ],
            }
          : current,
      );
      setMessage('');
    } catch (submitError) {
      setError(
        submitError instanceof WorkflowApiError
          ? submitError.message
          : 'Não foi possível enviar a mensagem.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading || !user || (!detail && !error)) {
    return <main className="loading-page">A carregar a conversa…</main>;
  }

  return (
    <main>
      <DashboardNav user={user} />
      <section className="conversation-shell">
        <div className="conversation-header">
          <div>
            <p className="eyebrow">Kiko AI</p>
            <h1 className="conversation-title">
              {detail?.conversation.title ?? 'Conversa'}
            </h1>
          </div>
          <Link className="secondary-link" href="/dashboard/kiko">
            Nova conversa
          </Link>
        </div>

        <div className="conversation-thread" aria-live="polite">
          {detail?.messages.map((item) => (
            <Message
              key={item.id}
              message={item}
              operation={detail.operations.find(
                (candidate) => candidate.command.id === item.command_id,
              )}
            />
          ))}
        </div>

        <form
          className="kiko-composer kiko-composer--compact"
          onSubmit={handleSubmit}
        >
          <label htmlFor="conversation-message">Continuar conversa</label>
          <textarea
            id="conversation-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            maxLength={10000}
            rows={4}
            placeholder="Acrescenta contexto ou faz o próximo pedido."
          />
          <div className="kiko-composer__actions">
            <span>
              Cada mensagem origina um comando operacional independente.
            </span>
            <button
              className="primary-button"
              disabled={submitting}
              type="submit"
            >
              {submitting ? 'A enviar…' : 'Enviar'}
            </button>
          </div>
        </form>
        {error && (
          <p className="form-message" role="alert">
            {error}
          </p>
        )}
      </section>
    </main>
  );
}

function Message({
  message,
  operation,
}: {
  message: ConversationMessage;
  operation?: ConversationOperation;
}) {
  return (
    <article
      className={`conversation-message conversation-message--${message.role}`}
    >
      <span>
        {message.role === 'user'
          ? 'Tu'
          : message.role === 'kiko'
            ? 'Kiko'
            : 'Sistema'}
      </span>
      <p>{message.content}</p>
      {message.command_id && (
        <Link href={`/dashboard/commands/${message.command_id}`}>
          Abrir comando operacional →
        </Link>
      )}
      {operation && <ConversationOperationStatus operation={operation} />}
    </article>
  );
}
