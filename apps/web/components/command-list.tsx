import type { Command } from '@agent/shared';
import Link from 'next/link';
import React from 'react';

import { StatusBadge } from './status-badge';
import { CanEdit } from '../lib/workspace-access';

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
      <p className="empty-state">Ainda não há comandos. Cria o primeiro.</p>
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
              <span>
                {new Date(command.created_at).toLocaleString('pt-PT')}
              </span>
              {command.duplicated_from_id && <span> · duplicado</span>}
            </div>
            <div className="command-row__meta">
              <StatusBadge status={command.status} />
              {commandProgress && (
                <span>
                  {commandProgress.completed}/{commandProgress.total} tarefas
                </span>
              )}
              <CanEdit>
                <div className="command-row__actions">
                  {onDuplicate && (
                    <button
                      type="button"
                      disabled={busyCommandId === command.id}
                      onClick={() => onDuplicate(command)}
                    >
                      Duplicar
                    </button>
                  )}
                  {command.archived_at
                    ? onRestore && (
                        <button
                          type="button"
                          disabled={busyCommandId === command.id}
                          onClick={() => onRestore(command)}
                        >
                          Restaurar
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
                          Arquivar
                        </button>
                      )}
                </div>
              </CanEdit>
            </div>
          </article>
        );
      })}
    </div>
  );
}
