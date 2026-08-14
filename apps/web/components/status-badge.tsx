import React from 'react';

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`workflow-badge workflow-badge--${status}`}>
      {status.replaceAll('_', ' ')}
    </span>
  );
}
