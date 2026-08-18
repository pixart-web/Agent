'use client';

import type { ApprovalRequest } from '@agent/shared';
import { useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import { StatusBadge } from '../../../components/status-badge';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import {
  approveAction,
  listApprovals,
  rejectAction,
  WorkflowApiError,
} from '../../../lib/workflow-client';

export default function ApprovalsPage() {
  const { user, loading: authLoading } = useAuthenticatedUser();
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [confirmations, setConfirmations] = useState<Record<string, boolean>>(
    {},
  );
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [error, setError] = useState('');

  async function load() {
    try {
      setApprovals(await listApprovals({ status: 'pending' }));
      setError('');
    } catch (loadError) {
      setError(
        loadError instanceof WorkflowApiError
          ? loadError.message
          : 'Unable to load approvals.',
      );
    }
  }

  useEffect(() => {
    if (user) void load();
  }, [user]);

  async function decide(approval: ApprovalRequest, approved: boolean) {
    try {
      if (approved) {
        await approveAction(
          approval.id,
          confirmations[approval.id] ?? false,
          reasons[approval.id],
        );
      } else {
        await rejectAction(approval.id, reasons[approval.id]);
      }
      await load();
    } catch (decisionError) {
      setError(
        decisionError instanceof WorkflowApiError
          ? decisionError.message
          : 'Unable to save the decision.',
      );
    }
  }

  if (authLoading || !user) {
    return <main className="loading-page">Loading approvals…</main>;
  }

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Human control</p>
          <h1>Approvals</h1>
          <p>Kiko pauses yellow and red actions before they reach the queue.</p>
        </div>
        <span>{approvals.length} pending</span>
      </section>
      {error && <p className="workflow-alert">{error}</p>}
      <div className="approval-grid">
        {approvals.map((approval) => (
          <article
            className={`workflow-panel approval-card approval-card--${approval.risk_level}`}
            key={approval.id}
          >
            <div className="workflow-panel__heading">
              <div>
                <p className="eyebrow">Kiko pede autorização</p>
                <h2>{approval.title}</h2>
              </div>
              <StatusBadge status={approval.risk_level} />
            </div>
            {approval.risk_level === 'red' && (
              <p className="high-risk-warning">
                Ação de alto risco — confirma explicitamente antes de continuar.
              </p>
            )}
            <p>{approval.description}</p>
            <dl className="execution-meta">
              <div>
                <dt>Task</dt>
                <dd>{approval.task_id}</dd>
              </div>
              <div>
                <dt>Requested</dt>
                <dd>{new Date(approval.requested_at).toLocaleString()}</dd>
              </div>
            </dl>
            {approval.risk_level === 'red' && (
              <label className="risk-confirmation">
                <input
                  type="checkbox"
                  checked={confirmations[approval.id] ?? false}
                  onChange={(event) =>
                    setConfirmations((current) => ({
                      ...current,
                      [approval.id]: event.target.checked,
                    }))
                  }
                />
                Compreendo que esta ação é de risco elevado.
              </label>
            )}
            <label>
              Decision note
              <textarea
                rows={3}
                value={reasons[approval.id] ?? ''}
                onChange={(event) =>
                  setReasons((current) => ({
                    ...current,
                    [approval.id]: event.target.value,
                  }))
                }
              />
            </label>
            <div className="approval-actions">
              <button
                className="primary-button"
                type="button"
                disabled={
                  approval.risk_level === 'red' &&
                  !(confirmations[approval.id] ?? false)
                }
                onClick={() => void decide(approval, true)}
              >
                Aprovar
              </button>
              <button
                className="danger-button"
                type="button"
                onClick={() => void decide(approval, false)}
              >
                Rejeitar
              </button>
            </div>
          </article>
        ))}
      </div>
      {!approvals.length && (
        <p className="empty-state">No actions are waiting for approval.</p>
      )}
    </main>
  );
}
