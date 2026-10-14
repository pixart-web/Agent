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

export default function SubscriptionPage() {
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
      .catch(() => setError('Unable to load subscription details.'));
  }, [user]);

  if (loading || !user)
    return <main className="loading-page">Loading subscription…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Commercial access</p>
          <h1>Subscription</h1>
        </div>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      {subscription && (
        <section className="workflow-panel">
          <div className="workflow-panel__heading">
            <div>
              <p className="eyebrow">Current plan</p>
              <h2>{subscription.plan.name}</h2>
            </div>
            <strong>{subscription.status}</strong>
          </div>
          <p>
            Current period ends{' '}
            {new Date(subscription.current_period_end).toLocaleDateString()}.
          </p>
          <p>
            {subscription.ai_tokens_used.toLocaleString()} of{' '}
            {subscription.plan.monthly_token_limit.toLocaleString()} AI tokens
            recorded.
          </p>
          <p>
            Billing provider:{' '}
            {subscription.billing_configuration_status.replaceAll('_', ' ')}.
          </p>
          {!subscription.cancel_at_period_end && (
            <button
              className="secondary-button"
              onClick={() => void cancelSubscription().then(setSubscription)}
            >
              Cancel at period end
            </button>
          )}
          {subscription.cancel_at_period_end && (
            <p className="workflow-alert">
              Cancellation is scheduled for the period end.
            </p>
          )}
        </section>
      )}
      <section className="agent-grid" aria-label="Available plans">
        {plans.map((plan) => (
          <article className="agent-card" key={plan.code}>
            <h2>{plan.name}</h2>
            <p>{plan.description}</p>
            <dl className="agent-metrics">
              <div>
                <dt>Seats</dt>
                <dd>{plan.seat_limit}</dd>
              </div>
              <div>
                <dt>Automations</dt>
                <dd>{plan.automation_limit}</dd>
              </div>
              <div>
                <dt>Retention</dt>
                <dd>{plan.retention_days}d</dd>
              </div>
            </dl>
            <p>
              {plan.integrations.length
                ? plan.integrations.join(', ')
                : 'No external integrations'}
            </p>
          </article>
        ))}
      </section>
      <p className="empty-state">
        Plan upgrades require owner-approved commercial configuration. No charge
        is simulated from this screen.
      </p>
    </main>
  );
}
