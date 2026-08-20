import React from 'react';

export function StatusBadge({
  status,
  label,
}: {
  status: string;
  label?: string;
}) {
  return (
    <span className={`workflow-badge workflow-badge--${status}`}>
      {label ?? status.replaceAll('_', ' ')}
    </span>
  );
}
