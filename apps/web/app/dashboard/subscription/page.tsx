'use client';

import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import {
  cancelSubscription,
  getSubscription,
  listCommercialPlans,
  type CommercialPlan,
  type Subscription,
} from '../../../lib/commercial-client';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import { useWorkspaceAccess } from '../../../lib/workspace-access';
import { label } from '../../../lib/labels';

export default function SubscriptionPage() {
  const { role } = useWorkspaceAccess();
  const { user, loading } = useAuthenticatedUser();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [plans, setPlans] = useState<CommercialPlan[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    void Promise.all([getSubscription(), listCommercialPlans()])
      .then(([nextSubscription, nextPlans]) => {
        setSubscription(nextSubscription);
        setPlans(nextPlans);
      })
      .catch(() => setError('Não foi possível carregar a subscrição.'));
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">A carregar a subscrição…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Acesso comercial</p>
          <h1>Subscrição</h1>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {subscription && (
        <section className="workflow-panel">
          <div className="workflow-panel__heading">
            <div>
              <p className="eyebrow">Plano atual</p>
              <h2>{subscription.plan.name}</h2>
            </div>
            <strong>{label(subscription.status)}</strong>
          </div>
          <p>
            Current period ends{' '}
            {new Date(subscription.current_period_end).toLocaleDateString(
              'pt-PT',
            )}
            .
          </p>
          <p>
            {subscription.ai_tokens_used.toLocaleString('pt-PT')} de{' '}
            {subscription.plan.monthly_token_limit.toLocaleString('pt-PT')}{' '}
            tokens de IA registados.
          </p>
          <p>
            Billing provider: {label(subscription.billing_configuration_status)}
            .
          </p>
          {!subscription.cancel_at_period_end && role === 'owner' && (
            <button
              className="secondary-button"
              onClick={() => void cancelSubscription().then(setSubscription)}
            >
              Cancelar no fim do período
            </button>
          )}
          {subscription.cancel_at_period_end && (
            <p className="workflow-alert">
              O cancelamento está agendado para o fim do período.
            </p>
          )}
        </section>
      )}
      <section className="agent-grid" aria-label="Planos disponíveis">
        {plans.map((plan) => (
          <article className="agent-card" key={plan.code}>
            <h2>{plan.name}</h2>
            <p>{plan.description}</p>
            <dl className="agent-metrics">
              <div>
                <dt>Lugares</dt>
                <dd>{plan.seat_limit}</dd>
              </div>
              <div>
                <dt>Automatizações</dt>
                <dd>{plan.automation_limit}</dd>
              </div>
              <div>
                <dt>Retenção</dt>
                <dd>{plan.retention_days}d</dd>
              </div>
            </dl>
            <p>
              {plan.integrations.length
                ? plan.integrations.join(', ')
                : 'Sem integrações externas'}
            </p>
          </article>
        ))}
      </section>
      <p className="empty-state">
        Mudar de plano exige configuração comercial aprovada pelo dono. Este
        ecrã não simula nenhuma cobrança.
      </p>
    </main>
  );
}
