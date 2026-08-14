'use client';

import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';
import {
  createCommand,
  WorkflowApiError,
} from '../../../../lib/workflow-client';

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
          : 'Unable to create the command right now.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading || !user) {
    return <main className="loading-page">Restoring your secure session…</main>;
  }

  return (
    <main>
      <DashboardNav user={user} />
      <section className="workflow-panel workflow-form-panel">
        <p className="eyebrow">New command</p>
        <h1 className="workflow-page-title">O que queres que o Agent faça?</h1>
        <form className="workflow-form" onSubmit={handleSubmit}>
          <label htmlFor="command-input">Operational instruction</label>
          <textarea
            id="command-input"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            rows={9}
            maxLength={10000}
            placeholder="Create a campaign to sell websites to restaurants."
          />
          <p className="form-hint">
            Não incluas palavras-passe, chaves API ou outros segredos no pedido.
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
      </section>
    </main>
  );
}
