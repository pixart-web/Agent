'use client';

import {
  TASK_PRIORITIES,
  TASK_STATUSES,
  type TaskPriority,
  type TaskStatus,
  type WorkspaceTask,
} from '@agent/shared';
import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import { StatusBadge } from '../../../components/status-badge';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import {
  listAgents,
  listWorkspaceTasks,
  type Agent,
} from '../../../lib/workflow-client';

export default function TasksPage() {
  const { user, loading: authLoading } = useAuthenticatedUser();
  const [tasks, setTasks] = useState<WorkspaceTask[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<TaskStatus | ''>('');
  const [priority, setPriority] = useState<TaskPriority | ''>('');
  const [agentId, setAgentId] = useState('');
  const [view, setView] = useState<'list' | 'board'>('list');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    let active = true;
    setLoading(true);
    async function loadTasks() {
      try {
        const loadedTasks = await listWorkspaceTasks({
          search: search || undefined,
          status: status || undefined,
          priority: priority || undefined,
          agentId: agentId || undefined,
          limit: 100,
        });
        const loadedAgents = await listAgents();
        if (!active) return;
        setTasks(loadedTasks);
        setAgents(loadedAgents);
        setError('');
      } catch {
        if (active) setError('Unable to load tasks right now.');
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadTasks();
    return () => {
      active = false;
    };
  }, [agentId, priority, search, status, user]);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchDraft.trim());
  }

  if (authLoading || !user) {
    return <main className="loading-page">Restoring your secure session…</main>;
  }

  return (
    <main>
      <DashboardNav user={user} />
      <div className="section-heading">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1 className="workflow-page-title">Tasks</h1>
        </div>
        <div className="view-switcher" aria-label="Task view">
          <button
            type="button"
            aria-pressed={view === 'list'}
            onClick={() => setView('list')}
          >
            List
          </button>
          <button
            type="button"
            aria-pressed={view === 'board'}
            onClick={() => setView('board')}
          >
            Board
          </button>
          <span>{tasks.length} visible</span>
        </div>
      </div>
      <form className="task-filters" onSubmit={submitSearch}>
        <label>
          Search
          <input
            type="search"
            value={searchDraft}
            maxLength={200}
            placeholder="Task, instruction or command…"
            onChange={(event) => setSearchDraft(event.target.value)}
          />
        </label>
        <label>
          Status
          <select
            value={status}
            onChange={(event) =>
              setStatus(event.target.value as TaskStatus | '')
            }
          >
            <option value="">All</option>
            {TASK_STATUSES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label>
          Priority
          <select
            value={priority}
            onChange={(event) =>
              setPriority(event.target.value as TaskPriority | '')
            }
          >
            <option value="">All</option>
            {TASK_PRIORITIES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label>
          Agent
          <select
            value={agentId}
            onChange={(event) => setAgentId(event.target.value)}
          >
            <option value="">All</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </label>
        <button className="secondary-button" type="submit">
          Search
        </button>
      </form>
      {error && (
        <p className="form-message" role="alert">
          {error}
        </p>
      )}
      {loading ? (
        <p>Loading tasks…</p>
      ) : tasks.length === 0 ? (
        <p className="empty-state">No tasks match these filters.</p>
      ) : view === 'list' ? (
        <div className="workspace-task-list">
          {tasks.map((task) => (
            <article className="workspace-task-row" key={task.id}>
              <div>
                <Link href={`/dashboard/tasks/${task.id}`}>{task.title}</Link>
                <p>{task.command_input}</p>
              </div>
              <span>{task.priority}</span>
              <span>
                {task.due_at
                  ? new Date(task.due_at).toLocaleDateString()
                  : 'No deadline'}
              </span>
              <StatusBadge status={task.status} />
            </article>
          ))}
        </div>
      ) : (
        <div className="task-board">
          {TASK_STATUSES.filter(
            (columnStatus) =>
              !status ||
              columnStatus === status ||
              tasks.some((task) => task.status === columnStatus),
          ).map((columnStatus) => {
            const columnTasks = tasks.filter(
              (task) => task.status === columnStatus,
            );
            return (
              <section className="task-board__column" key={columnStatus}>
                <div className="task-board__heading">
                  <StatusBadge status={columnStatus} />
                  <span>{columnTasks.length}</span>
                </div>
                <div className="task-board__cards">
                  {columnTasks.map((task) => (
                    <article key={task.id}>
                      <Link href={`/dashboard/tasks/${task.id}`}>
                        {task.title}
                      </Link>
                      <p>{task.command_input}</p>
                      <span>{task.priority}</span>
                      <span>
                        {task.due_at
                          ? new Date(task.due_at).toLocaleDateString()
                          : 'No deadline'}
                      </span>
                    </article>
                  ))}
                  {columnTasks.length === 0 && <p>No tasks</p>}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </main>
  );
}
