import React from 'react';

import { aiErrorHint } from '../lib/ai-errors';

/** An error message with a recovery hint when it is a known local AI problem. */
export function AiErrorNotice({
  message,
  className = 'workflow-alert',
}: {
  message: string;
  className?: string;
}) {
  const hint = aiErrorHint(message);
  return (
    <div className={className} role="alert">
      <p>{message}</p>
      {hint && <p className="ai-error-hint">{hint}</p>}
    </div>
  );
}
