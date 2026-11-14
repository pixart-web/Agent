import type { Command } from '@agent/shared';
import Link from 'next/link';
import React from 'react';

import { StatusBadge } from './status-badge';

export type CommandProgress = { completed: number; total: number };

export function CommandList({
  commands,
  progress = {},
  busyCommandId,
  onArchive,
  onRestore,
  onDuplicate,
}: {
  commands: Command[];
  progress?: Record<string, CommandProgress>;
  busyCommandId?: string | null;
  onArchive?: (command: Command) => void;
  onRestore?: (command: Command) => void;
  onDuplicate?: (command: Command) => void;
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
          <article className="command-row" key={command.id}>
            <div>
              <Link
                className="command-row__link"
                href={`/dashboard/commands/${command.id}`}
              >
                {command.input}
              </Link>
              <span>{new Date(command.created_at).toLocaleString()}</span>
              {command.duplicated_from_id && <span> · duplicated</span>}
            </div>
            <div className="command-row__meta">
              <StatusBadge status={command.status} />
              {commandProgress && (
                <span>
                  {commandProgress.completed}/{commandProgress.total} tasks
                </span>
              )}
              <div className="command-row__actions">
                {onDuplicate && (
                  <button
                    type="button"
                    disabled={busyCommandId === command.id}
                    onClick={() => onDuplicate(command)}
                  >
                    Duplicate
                  </button>
                )}
                {command.archived_at
                  ? onRestore && (
                      <button
                        type="button"
                        disabled={busyCommandId === command.id}
                        onClick={() => onRestore(command)}
                      >
                        Restore
                      </button>
                    )
                  : onArchive &&
                    ['completed', 'failed', 'cancelled'].includes(
                      command.status,
                    ) && (
                      <button
                        type="button"
                        disabled={busyCommandId === command.id}
                        onClick={() => onArchive(command)}
                      >
                        Archive
                      </button>
                    )}
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}
