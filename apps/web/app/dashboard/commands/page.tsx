'use client';

import type { Command } from '@agent/shared';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import {
  CommandList,
  type CommandProgress,
} from '../../../components/command-list';
import { DashboardNav } from '../../../components/dashboard-nav';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import {
  getPlan,
  listCommands,
  listTasks,
  WorkflowApiError,
} from '../../../lib/workflow-client';

export default function CommandsPage() {
  const { user, loading: authLoading } = useAuthenticatedUser();
  const [commands, setCommands] = useState<Command[]>([]);
  const [progress, setProgress] = useState<Record<string, CommandProgress>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    let active = true;

    async function loadCommands() {
      try {
        const commandList = await listCommands({ limit: 100 });
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
  }, [user]);

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
      {error && (
        <p className="form-message" role="alert">
          {error}
        </p>
      )}
      {loading ? (
        <p aria-live="polite">Loading commands…</p>
      ) : (
        <CommandList commands={commands} progress={progress} />
      )}
    </main>
  );
}
