import React from 'react';

import { label as statusLabel } from '../lib/labels';

export function StatusBadge({
  status,
  label,
}: {
  status: string;
  label?: string;
}) {
  return (
    <span className={`workflow-badge workflow-badge--${status}`}>
      {label ?? statusLabel(status)}
    </span>
  );
}
