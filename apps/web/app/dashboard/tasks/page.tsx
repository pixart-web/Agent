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
import { label } from '../../../lib/labels';
import { failureMessage } from '../../../lib/api-messages';

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
      } catch (failure) {
        if (active)
          setError(
            failureMessage(
              failure,
              'Não foi possível carregar as tarefas agora.',
            ),
          );
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
    return <main className="loading-page">A restaurar a sessão segura…</main>;
  }

  return (
    <main>
      <DashboardNav user={user} />
      <div className="section-heading">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1 className="workflow-page-title">Tarefas</h1>
        </div>
        <div className="view-switcher" aria-label="Vista de tarefas">
          <button
            type="button"
            aria-pressed={view === 'list'}
            onClick={() => setView('list')}
          >
            Lista
          </button>
          <button
            type="button"
            aria-pressed={view === 'board'}
            onClick={() => setView('board')}
          >
            Quadro
          </button>
          <span>{tasks.length} visíveis</span>
        </div>
      </div>
      <form className="task-filters" onSubmit={submitSearch}>
        <label>
          Pesquisar
          <input
            type="search"
            value={searchDraft}
            maxLength={200}
            placeholder="Tarefa, instrução ou comando…"
            onChange={(event) => setSearchDraft(event.target.value)}
          />
        </label>
        <label>
          Estado
          <select
            value={status}
            onChange={(event) =>
              setStatus(event.target.value as TaskStatus | '')
            }
          >
            <option value="">Todos</option>
            {TASK_STATUSES.map((value) => (
              <option key={value} value={value}>
                {label(value)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Prioridade
          <select
            value={priority}
            onChange={(event) =>
              setPriority(event.target.value as TaskPriority | '')
            }
          >
            <option value="">Todos</option>
            {TASK_PRIORITIES.map((value) => (
              <option key={value} value={value}>
                {label(value)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Agente
          <select
            value={agentId}
            onChange={(event) => setAgentId(event.target.value)}
          >
            <option value="">Todos</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </label>
        <button className="secondary-button" type="submit">
          Pesquisar
        </button>
      </form>
      {error && (
        <p className="form-message" role="alert">
          {error}
        </p>
      )}
      {loading ? (
        <p>A carregar as tarefas…</p>
      ) : tasks.length === 0 ? (
        <p className="empty-state">
          Nenhuma tarefa corresponde a estes filtros.
        </p>
      ) : view === 'list' ? (
        <div className="workspace-task-list">
          {tasks.map((task) => (
            <article className="workspace-task-row" key={task.id}>
              <div>
                <Link href={`/dashboard/tasks/${task.id}`}>{task.title}</Link>
                <p>{task.command_input}</p>
              </div>
              <span>{label(task.priority)}</span>
              <span>
                {task.due_at
                  ? new Date(task.due_at).toLocaleDateString('pt-PT')
                  : 'Sem prazo'}
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
                      <span>{label(task.priority)}</span>
                      <span>
                        {task.due_at
                          ? new Date(task.due_at).toLocaleDateString('pt-PT')
                          : 'Sem prazo'}
                      </span>
                    </article>
                  ))}
                  {columnTasks.length === 0 && <p>Sem tarefas</p>}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </main>
  );
}
