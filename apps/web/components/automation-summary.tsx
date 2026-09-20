import type { AutomationRun } from '@agent/shared';
import Link from 'next/link';
import React from 'react';

export function AutomationPolicyNote() {
  return (
    <p>
      A trigger creates a correlated command only. It cannot approve plans,
      approve actions, lower risk, or execute external tools. Event payloads are
      untrusted data and are not interpolated into the command.
    </p>
  );
}

export function AutomationRunSummary({ run }: { run: AutomationRun }) {
  return (
    <div>
      <p className="eyebrow">
        {run.trigger_type} · {run.status}
      </p>
      <p>Correlation: {run.correlation_id}</p>
      {run.skipped_reason && <p>Guardrail: {run.skipped_reason}</p>}
      {run.command_id && (
        <Link href={`/dashboard/commands/${run.command_id}`}>
          Open generated command
        </Link>
      )}
    </div>
  );
}
