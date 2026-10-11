'use client';

import type {
  ApprovalDetail,
  ApprovalRequest,
  ApprovalStatus,
} from '@agent/shared';
import { useCallback, useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import { StatusBadge } from '../../../components/status-badge';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import {
  approveAction,
  addApprovalComment,
  getApprovalDetail,
  listApprovals,
  rejectAction,
  WorkflowApiError,
} from '../../../lib/workflow-client';

export default function ApprovalsPage() {
  const { user, loading: authLoading } = useAuthenticatedUser();
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [details, setDetails] = useState<Record<string, ApprovalDetail>>({});
  const [filter, setFilter] = useState<ApprovalStatus | ''>('pending');
  const [comments, setComments] = useState<Record<string, string>>({});
  const [confirmations, setConfirmations] = useState<Record<string, boolean>>(
    {},
  );
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const loaded = await listApprovals({ status: filter || undefined });
      const loadedDetails: Record<string, ApprovalDetail> = {};
      for (const approval of loaded) {
        loadedDetails[approval.id] = await getApprovalDetail(approval.id);
      }
      setApprovals(loaded);
      setDetails(loadedDetails);
      setError('');
    } catch (loadError) {
      setError(
        loadError instanceof WorkflowApiError
          ? loadError.message
          : 'Unable to load approvals.',
      );
    }
  }, [filter]);

  useEffect(() => {
    if (user) void load();
  }, [load, user]);

  async function comment(approvalId: string) {
    const body = comments[approvalId]?.trim();
    if (!body) return;
    try {
      await addApprovalComment(approvalId, body);
      setComments((current) => ({ ...current, [approvalId]: '' }));
      await load();
    } catch {
      setError('Unable to add the approval comment.');
    }
  }

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
        <label>
          View
          <select
            value={filter}
            onChange={(event) =>
              setFilter(event.target.value as ApprovalStatus | '')
            }
          >
            <option value="pending">Pending</option>
            <option value="">All history</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="expired">Expired</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </label>
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
            <p className="approval-description">{approval.description}</p>
            {details[approval.id] && (
              <div className="approval-evidence">
                <dl className="execution-meta">
                  <div>
                    <dt>Requesting agent</dt>
                    <dd>{details[approval.id].requesting_agent}</dd>
                  </div>
                  <div>
                    <dt>Target integration</dt>
                    <dd>{details[approval.id].target_integration}</dd>
                  </div>
                  <div>
                    <dt>Tool</dt>
                    <dd>{details[approval.id].action.tool_name}</dd>
                  </div>
                  <div>
                    <dt>Expires</dt>
                    <dd>
                      {approval.expires_at
                        ? new Date(approval.expires_at).toLocaleString()
                        : 'No expiry'}
                    </dd>
                  </div>
                </dl>
                <details>
                  <summary>Exact action payload</summary>
                  <pre>
                    {JSON.stringify(
                      details[approval.id].action.input_payload,
                      null,
                      2,
                    )}
                  </pre>
                </details>
              </div>
            )}
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
            {approval.status === 'pending' && approval.risk_level === 'red' && (
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
            {approval.status === 'pending' && (
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
            )}
            {approval.status === 'pending' && (
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
            )}
            <div className="approval-comments">
              <h3>Discussion & history</h3>
              {details[approval.id]?.comments.map((item) => (
                <p key={item.id}>
                  <strong>Comment</strong> ·{' '}
                  {new Date(item.created_at).toLocaleString()}
                  <br />
                  {item.body}
                </p>
              ))}
              {details[approval.id]?.history.map((item, index) => (
                <p key={`${item.event_type}-${index}`}>
                  <strong>{item.event_type.replaceAll('_', ' ')}</strong> ·{' '}
                  {new Date(item.created_at).toLocaleString()}
                </p>
              ))}
              <label>
                Add comment
                <textarea
                  rows={2}
                  maxLength={2000}
                  value={comments[approval.id] ?? ''}
                  onChange={(event) =>
                    setComments((current) => ({
                      ...current,
                      [approval.id]: event.target.value,
                    }))
                  }
                />
              </label>
              <button
                className="secondary-button"
                type="button"
                disabled={!comments[approval.id]?.trim()}
                onClick={() => void comment(approval.id)}
              >
                Comment
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
