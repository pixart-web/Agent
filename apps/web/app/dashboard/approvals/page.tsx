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
import { CanEdit } from '../../../lib/workspace-access';
import { label } from '../../../lib/labels';

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
          : 'Não foi possível carregar as aprovações.',
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
      setError('Não foi possível adicionar o comentário.');
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
          : 'Não foi possível guardar a decisão.',
      );
    }
  }

  if (authLoading || !user) {
    return <main className="loading-page">A carregar as aprovações…</main>;
  }

  return (
    <main>
      <DashboardNav user={user} />
      <section className="section-heading">
        <div>
          <p className="eyebrow">Controlo humano</p>
          <h1>Aprovações</h1>
          <p>
            O Kiko suspende as ações amarelas e vermelhas antes de entrarem na
            fila.
          </p>
        </div>
        <label>
          Ver
          <select
            value={filter}
            onChange={(event) =>
              setFilter(event.target.value as ApprovalStatus | '')
            }
          >
            <option value="pending">Pendentes</option>
            <option value="">Todo o histórico</option>
            <option value="approved">Aprovado</option>
            <option value="rejected">Rejeitado</option>
            <option value="expired">Expirado</option>
            <option value="cancelled">Cancelado</option>
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
                    <dt>Agente que pede</dt>
                    <dd>{details[approval.id].requesting_agent}</dd>
                  </div>
                  <div>
                    <dt>Integração de destino</dt>
                    <dd>{details[approval.id].target_integration}</dd>
                  </div>
                  <div>
                    <dt>Ferramenta</dt>
                    <dd>{details[approval.id].action.tool_name}</dd>
                  </div>
                  <div>
                    <dt>Expira</dt>
                    <dd>
                      {approval.expires_at
                        ? new Date(approval.expires_at).toLocaleString('pt-PT')
                        : 'Sem validade'}
                    </dd>
                  </div>
                </dl>
                <details>
                  <summary>Dados exatos da ação</summary>
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
                <dt>Tarefa</dt>
                <dd>{approval.task_id}</dd>
              </div>
              <div>
                <dt>Pedido em</dt>
                <dd>
                  {new Date(approval.requested_at).toLocaleString('pt-PT')}
                </dd>
              </div>
            </dl>
            <CanEdit>
              {approval.status === 'pending' &&
                approval.risk_level === 'red' && (
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
                  Nota da decisão
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
            </CanEdit>
            <div className="approval-comments">
              <h3>Discussão e histórico</h3>
              {details[approval.id]?.comments.map((item) => (
                <p key={item.id}>
                  <strong>Comentar</strong> ·{' '}
                  {new Date(item.created_at).toLocaleString('pt-PT')}
                  <br />
                  {item.body}
                </p>
              ))}
              {details[approval.id]?.history.map((item, index) => (
                <p key={`${item.event_type}-${index}`}>
                  <strong>{label(item.event_type)}</strong> ·{' '}
                  {new Date(item.created_at).toLocaleString('pt-PT')}
                </p>
              ))}
              <CanEdit>
                <label>
                  Adicionar comentário
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
                  Comentar
                </button>
              </CanEdit>
            </div>
          </article>
        ))}
      </div>
      {!approvals.length && (
        <p className="empty-state">Não há ações à espera de aprovação.</p>
      )}
    </main>
  );
}
