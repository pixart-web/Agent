'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useEffect, useState } from 'react';
import type { Conversation } from '@agent/shared';

import { DashboardNav } from '../../../components/dashboard-nav';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import {
  createConversation,
  listConversations,
  WorkflowApiError,
} from '../../../lib/workflow-client';

export default function KikoPage() {
  const router = useRouter();
  const { user, loading } = useAuthenticatedUser();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    let active = true;
    listConversations()
      .then((items) => active && setConversations(items))
      .catch(
        () => active && setError('Não foi possível carregar as conversas.'),
      );
    return () => {
      active = false;
    };
  }, [user]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = message.trim();
    if (!content) return;
    setSubmitting(true);
    setError('');
    try {
      const turn = await createConversation(content);
      router.push(`/dashboard/kiko/${turn.conversation.id}`);
    } catch (submitError) {
      setError(
        submitError instanceof WorkflowApiError
          ? submitError.message
          : 'Não foi possível iniciar a conversa.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading || !user) {
    return <main className="loading-page">A restaurar a sessão segura…</main>;
  }

  return (
    <main>
      <DashboardNav user={user} />
      <section className="kiko-hero">
        <p className="eyebrow">Kiko AI</p>
        <h1 className="workflow-page-title">O que vamos fazer?</h1>
        <p className="subtitle">
          Conversa com Kiko. Cada pedido cria um comando rastreável, sujeito às
          mesmas regras de planeamento, execução e aprovação.
        </p>
        <form className="kiko-composer" onSubmit={handleSubmit}>
          <label htmlFor="kiko-message">Novo pedido</label>
          <textarea
            id="kiko-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            maxLength={10000}
            rows={5}
            placeholder="Prepara o lançamento do nosso novo serviço para clientes B2B."
          />
          <div className="kiko-composer__actions">
            <span>
              Não incluas palavras-passe, chaves API ou outros segredos.
            </span>
            <button
              className="primary-button"
              disabled={submitting}
              type="submit"
            >
              {submitting ? 'A criar…' : 'Enviar para Kiko'}
            </button>
          </div>
        </form>
        {error && (
          <p className="form-message" role="alert">
            {error}
          </p>
        )}
      </section>

      <section
        className="workflow-panel"
        aria-labelledby="recent-conversations"
      >
        <div className="workflow-panel__heading">
          <h2 id="recent-conversations">Conversas recentes</h2>
          <span>{conversations.length}</span>
        </div>
        {conversations.length === 0 ? (
          <p className="empty-copy">
            Ainda não existem conversas neste workspace.
          </p>
        ) : (
          <div className="conversation-list">
            {conversations.map((conversation) => (
              <Link
                key={conversation.id}
                href={`/dashboard/kiko/${conversation.id}`}
              >
                <strong>{conversation.title}</strong>
                <span>
                  {new Date(conversation.updated_at).toLocaleString()}
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
