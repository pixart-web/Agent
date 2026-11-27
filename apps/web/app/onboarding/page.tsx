'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import {
  AuthClientError,
  getOnboarding,
  updateOnboarding,
} from '../../lib/auth-client';
import type { OnboardingState } from '../../lib/auth-types';
import { useAuthenticatedUser } from '../../lib/use-authenticated-user';
import { KikoLogo } from '../../components/kiko/kiko-logo';

const objectiveOptions = [
  'Organizar tarefas do negócio',
  'Preparar campanhas de marketing',
  'Analisar o pipeline de clientes',
  'Planear reuniões e seguimentos',
  'Coordenar o trabalho de desenvolvimento',
];

export default function OnboardingPage() {
  const router = useRouter();
  const { user, loading } = useAuthenticatedUser(false);
  const [state, setState] = useState<OnboardingState | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [objectives, setObjectives] = useState<string[]>([]);
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) return;
    if (user.onboarding_completed_at) {
      router.replace('/dashboard');
      return;
    }
    void getOnboarding()
      .then((value) => {
        setState(value);
        setName(value.company_name);
        setDescription(value.company_description ?? '');
        setObjectives(value.primary_objectives);
      })
      .catch((error) =>
        setMessage(
          error instanceof AuthClientError
            ? error.message
            : 'Não foi possível carregar a configuração inicial.',
        ),
      );
  }, [router, user]);

  function toggleObjective(value: string) {
    setObjectives((current) =>
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    );
  }

  async function complete(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage('');
    const readOnly = state ? !state.can_edit_company : false;
    try {
      await updateOnboarding(
        readOnly
          ? { step: 8, complete: true }
          : {
              step: 8,
              company_name: name.trim(),
              company_description: description.trim(),
              primary_objectives: objectives,
              complete: true,
            },
      );
      router.replace(readOnly ? '/dashboard' : '/dashboard/commands/new');
    } catch (error) {
      setMessage(
        error instanceof AuthClientError
          ? error.message
          : 'Não foi possível guardar a configuração inicial.',
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading || !user || !state) {
    return <main className="loading-page">A preparar o teu workspace…</main>;
  }

  if (!state.can_edit_company) {
    return (
      <main className="onboarding-shell">
        <section className="onboarding-card">
          <KikoLogo />
          <p className="eyebrow">Bem-vindo ao Kiko</p>
          <h1>Junta-te a {state.company_name}</h1>
          <p className="lede">
            A tua equipa já configurou este workspace. Só donos e
            administradores podem alterar o perfil da empresa.
          </p>
          <dl className="onboarding-profile">
            <dt>Empresa</dt>
            <dd>{state.company_name}</dd>
            <dt>O que a empresa faz</dt>
            <dd>{state.company_description || 'Ainda não preenchido.'}</dd>
            <dt>Objetivos principais</dt>
            <dd>
              {state.primary_objectives.length > 0 ? (
                <ul>
                  {state.primary_objectives.map((objective) => (
                    <li key={objective}>{objective}</li>
                  ))}
                </ul>
              ) : (
                'Ainda não preenchido.'
              )}
            </dd>
          </dl>
          <form className="auth-form" onSubmit={complete}>
            <div className="onboarding-actions">
              <button
                className="primary-button"
                disabled={saving}
                type="submit"
              >
                {saving ? 'A abrir…' : 'Continuar para o workspace'}
              </button>
            </div>
          </form>
          {message && (
            <p className="form-message" role="status">
              {message}
            </p>
          )}
        </section>
      </main>
    );
  }

  return (
    <main className="onboarding-shell">
      <section className="onboarding-card">
        <KikoLogo />
        <p className="eyebrow">Bem-vindo ao Kiko</p>
        <h1>Configura o workspace da tua empresa</h1>
        <p className="lede">
          Diz ao Kiko o que a tua empresa faz e o que queres alcançar. Podes
          ligar integrações opcionais depois desta configuração.
        </p>
        <form className="auth-form" onSubmit={complete}>
          <label>
            Nome da empresa
            <input
              required
              minLength={2}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label>
            O que faz a tua empresa?
            <textarea
              required
              maxLength={2000}
              rows={5}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
          <fieldset className="onboarding-objectives">
            <legend>Objetivos principais</legend>
            {objectiveOptions.map((objective) => (
              <label key={objective}>
                <input
                  type="checkbox"
                  checked={objectives.includes(objective)}
                  onChange={() => toggleObjective(objective)}
                />
                <span>{objective}</span>
              </label>
            ))}
          </fieldset>
          <div className="onboarding-actions">
            <button
              className="primary-button"
              disabled={saving || objectives.length === 0}
              type="submit"
            >
              {saving
                ? 'A guardar…'
                : 'Concluir e criar o meu primeiro comando'}
            </button>
            <span className="form-note">
              As integrações opcionais podem ser ligadas depois da configuração.
            </span>
          </div>
        </form>
        {message && (
          <p className="form-message" role="status">
            {message}
          </p>
        )}
        <p className="form-note">
          Nenhuma ação externa é feita durante a configuração.
        </p>
      </section>
    </main>
  );
}
