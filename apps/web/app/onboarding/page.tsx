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

const objectiveOptions = [
  'Organize business tasks',
  'Prepare marketing campaigns',
  'Analyze the customer pipeline',
  'Plan meetings and follow-ups',
  'Coordinate development work',
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
            : 'Unable to load onboarding.',
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
          : 'Unable to save onboarding.',
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading || !user || !state) {
    return <main className="loading-page">Preparing your workspace…</main>;
  }

  if (!state.can_edit_company) {
    return (
      <main className="onboarding-shell">
        <section className="onboarding-card">
          <p className="eyebrow">Welcome to Kiko</p>
          <h1>Join {state.company_name}</h1>
          <p className="lede">
            Your team has already set up this workspace. Only owners and admins
            can change the company profile.
          </p>
          <dl className="onboarding-profile">
            <dt>Company</dt>
            <dd>{state.company_name}</dd>
            <dt>What the company does</dt>
            <dd>{state.company_description || 'Not filled in yet.'}</dd>
            <dt>Primary objectives</dt>
            <dd>
              {state.primary_objectives.length > 0 ? (
                <ul>
                  {state.primary_objectives.map((objective) => (
                    <li key={objective}>{objective}</li>
                  ))}
                </ul>
              ) : (
                'Not filled in yet.'
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
                {saving ? 'Opening…' : 'Continue to the workspace'}
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
        <p className="eyebrow">Welcome to Kiko</p>
        <h1>Set up your company workspace</h1>
        <p className="lede">
          Tell Kiko what your company does and what you want to achieve. You can
          connect optional integrations after this setup.
        </p>
        <form className="auth-form" onSubmit={complete}>
          <label>
            Company name
            <input
              required
              minLength={2}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label>
            What does your company do?
            <textarea
              required
              maxLength={2000}
              rows={5}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
          <fieldset className="onboarding-objectives">
            <legend>Primary objectives</legend>
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
              {saving ? 'Saving…' : 'Finish and create my first command'}
            </button>
            <span className="form-note">
              Optional integrations can be connected after setup.
            </span>
          </div>
        </form>
        {message && (
          <p className="form-message" role="status">
            {message}
          </p>
        )}
        <p className="form-note">
          No external action is performed during setup.
        </p>
      </section>
    </main>
  );
}
