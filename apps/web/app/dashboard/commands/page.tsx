'use client';

import type { Command } from '@agent/shared';
import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import {
  CommandList,
  type CommandProgress,
} from '../../../components/command-list';
import { DashboardNav } from '../../../components/dashboard-nav';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import {
  getPlan,
  archiveCommand,
  duplicateCommand,
  listCommands,
  listTasks,
  restoreCommand,
  WorkflowApiError,
} from '../../../lib/workflow-client';

export default function CommandsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuthenticatedUser();
  const [commands, setCommands] = useState<Command[]>([]);
  const [progress, setProgress] = useState<Record<string, CommandProgress>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [includeArchived, setIncludeArchived] = useState(false);
  const [busyCommandId, setBusyCommandId] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let active = true;

    async function loadCommands() {
      try {
        const commandList = await listCommands({
          limit: 100,
          search: search || undefined,
          includeArchived,
        });
        const progressEntries = await Promise.all(
          commandList.map(async (command) => {
            try {
              const plan = await getPlan(command.id);
              const tasks = await listTasks(plan.id);
              return [
                command.id,
                {
                  completed: tasks.filter((task) => task.status === 'completed')
                    .length,
                  total: tasks.length,
                },
              ] as const;
            } catch (loadError) {
              if (
                loadError instanceof WorkflowApiError &&
                loadError.status === 404
              ) {
                return null;
              }
              throw loadError;
            }
          }),
        );
        if (active) {
          setCommands(commandList);
          setProgress(
            Object.fromEntries(
              progressEntries.filter((entry) => entry !== null),
            ),
          );
        }
      } catch {
        if (active) setError('Unable to load commands right now.');
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadCommands();
    return () => {
      active = false;
    };
  }, [includeArchived, search, user]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchDraft.trim());
  }

  async function mutateCommand(
    command: Command,
    action: 'archive' | 'restore' | 'duplicate',
  ) {
    setBusyCommandId(command.id);
    setError('');
    try {
      if (action === 'duplicate') {
        const duplicate = await duplicateCommand(command.id);
        router.push(`/dashboard/commands/${duplicate.id}`);
        return;
      }
      const updated =
        action === 'archive'
          ? await archiveCommand(command.id)
          : await restoreCommand(command.id);
      setCommands((current) =>
        action === 'archive' && !includeArchived
          ? current.filter((item) => item.id !== updated.id)
          : current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (mutationError) {
      setError(
        mutationError instanceof WorkflowApiError
          ? mutationError.message
          : 'Unable to update the command right now.',
      );
    } finally {
      setBusyCommandId(null);
    }
  }

  if (authLoading || !user) {
    return <main className="loading-page">Restoring your secure session…</main>;
  }

  return (
    <main>
      <DashboardNav user={user} />
      <div className="section-heading">
        <div>
          <p className="eyebrow">Operations</p>
          <h1 className="workflow-page-title">Commands</h1>
        </div>
        <Link className="primary-link" href="/dashboard/commands/new">
          New command
        </Link>
      </div>
      <form className="command-filters" onSubmit={handleSearch}>
        <label>
          Search commands
          <input
            type="search"
            value={searchDraft}
            maxLength={200}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder="Campaign, client, objective…"
          />
        </label>
        <button className="secondary-button" type="submit">
          Search
        </button>
        <label className="command-filters__check">
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(event) => setIncludeArchived(event.target.checked)}
          />
          Include archived
        </label>
      </form>
      {error && (
        <p className="form-message" role="alert">
          {error}
        </p>
      )}
      {loading ? (
        <p aria-live="polite">Loading commands…</p>
      ) : (
        <CommandList
          commands={commands}
          progress={progress}
          busyCommandId={busyCommandId}
          onArchive={(command) => void mutateCommand(command, 'archive')}
          onRestore={(command) => void mutateCommand(command, 'restore')}
          onDuplicate={(command) => void mutateCommand(command, 'duplicate')}
        />
      )}
    </main>
  );
}
