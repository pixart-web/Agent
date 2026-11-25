import type { ConversationOperation } from '@agent/shared';
import React from 'react';
import { label } from '../lib/labels';
import { apiMessage } from '../lib/api-messages';

export function ConversationOperationStatus({
  operation,
}: {
  operation: ConversationOperation;
}) {
  const tasks = Object.entries(operation.task_counts);
  return (
    <section className="conversation-operation" aria-label="Estado operacional">
      <div className="conversation-operation__heading">
        <strong>Estado operacional</strong>
        <span
          className={`workflow-badge workflow-badge--${operation.command.status}`}
        >
          {label(operation.command.status)}
        </span>
      </div>
      {operation.supervisor_status && (
        <p>Supervisor: {label(operation.supervisor_status)}</p>
      )}
      {operation.plan && (
        <div className="conversation-operation__plan">
          <strong>{operation.plan.title}</strong>
          <p>{operation.plan.objective}</p>
          <span>Plano {label(operation.plan.status)}</span>
        </div>
      )}
      {tasks.length > 0 && (
        <p>
          Tarefas:{' '}
          {tasks
            .map(([status, count]) => `${count} ${label(status).toLowerCase()}`)
            .join(' · ')}
        </p>
      )}
      {operation.pending_approvals > 0 && (
        <p className="conversation-operation__attention">
          {operation.pending_approvals}{' '}
          {operation.pending_approvals === 1
            ? 'aprovação pendente'
            : 'aprovações pendentes'}
        </p>
      )}
      {operation.latest_error && (
        <p className="conversation-operation__error" role="alert">
          {apiMessage(operation.latest_error)}
        </p>
      )}
    </section>
  );
}
