import type { Command } from '@agent/shared';
import Link from 'next/link';
import React from 'react';

import { StatusBadge } from './status-badge';

export type CommandProgress = { completed: number; total: number };

export function CommandList({
  commands,
  progress = {},
}: {
  commands: Command[];
  progress?: Record<string, CommandProgress>;
}) {
  if (commands.length === 0) {
    return (
      <p className="empty-state">No commands yet. Create the first one.</p>
    );
  }

  return (
    <div className="command-list">
      {commands.map((command) => {
        const commandProgress = progress[command.id];
        return (
          <Link
            className="command-row"
            href={`/dashboard/commands/${command.id}`}
            key={command.id}
          >
            <div>
              <p>{command.input}</p>
              <span>{new Date(command.created_at).toLocaleString()}</span>
            </div>
            <div className="command-row__meta">
              <StatusBadge status={command.status} />
              {commandProgress && (
                <span>
                  {commandProgress.completed}/{commandProgress.total} tasks
                </span>
              )}
            </div>
          </Link>
        );
      })}
    </div>
  );
}
