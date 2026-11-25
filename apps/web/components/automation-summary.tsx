import type { AutomationRun } from '@agent/shared';
import Link from 'next/link';
import React from 'react';
import { label } from '../lib/labels';

export function AutomationPolicyNote() {
  return (
    <p>
      Um gatilho apenas cria um comando correlacionado. Não pode aprovar planos
      ou ações, baixar o risco nem executar ferramentas externas. Os dados do
      evento não são de confiança e nunca entram no comando.
    </p>
  );
}

export function AutomationRunSummary({ run }: { run: AutomationRun }) {
  return (
    <div>
      <p className="eyebrow">
        {label(run.trigger_type)} · {label(run.status)}
      </p>
      <p>Correlação: {run.correlation_id}</p>
      {run.skipped_reason && (
        <p>Limite de segurança: {label(run.skipped_reason)}</p>
      )}
      {run.command_id && (
        <Link href={`/dashboard/commands/${run.command_id}`}>
          Abrir o comando criado
        </Link>
      )}
    </div>
  );
}
