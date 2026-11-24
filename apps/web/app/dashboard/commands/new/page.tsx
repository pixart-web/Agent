'use client';

import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';
import {
  createCommand,
  WorkflowApiError,
} from '../../../../lib/workflow-client';
import { CanEdit } from '../../../../lib/workspace-access';

export default function NewCommandPage() {
  const router = useRouter();
  const { user, loading } = useAuthenticatedUser();
  const [input, setInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!input.trim()) {
      setError('Describe what you want Agent to do.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const command = await createCommand(input.trim());
      router.push(`/dashboard/commands/${command.id}`);
    } catch (submitError) {
      setError(
        submitError instanceof WorkflowApiError
          ? submitError.message
          : 'Não foi possível criar o comando agora.',
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
      <section className="workflow-panel workflow-form-panel">
        <p className="eyebrow">Novo comando</p>
        <h1 className="workflow-page-title">O que queres que o Kiko faça?</h1>
        <CanEdit
          fallback={
            <p className="form-hint">
              Tens acesso só de leitura a este workspace. Um dono ou admin pode
              dar-te acesso de edição para criares comandos.
            </p>
          }
        >
          <form className="workflow-form" onSubmit={handleSubmit}>
            <label htmlFor="command-input">Instrução operacional</label>
            <textarea
              id="command-input"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              rows={9}
              maxLength={10000}
              placeholder="Criar uma campanha para vender websites a restaurantes."
            />
            <p className="form-hint">
              Não incluas palavras-passe, chaves API ou outros segredos no
              pedido.
            </p>
            {error && (
              <p className="form-message" role="alert">
                {error}
              </p>
            )}
            <button
              className="primary-button"
              type="submit"
              disabled={submitting}
            >
              {submitting ? 'A criar…' : 'Criar comando'}
            </button>
          </form>
        </CanEdit>
      </section>
    </main>
  );
}
