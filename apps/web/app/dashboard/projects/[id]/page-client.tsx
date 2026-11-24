'use client';

import {
  PROJECT_STATUSES,
  type ProjectDetail,
  type ProjectStatus,
} from '@agent/shared';
import Link from 'next/link';
import { useParams } from '../../../../lib/route-params';
import { FormEvent, useCallback, useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { StatusBadge } from '../../../../components/status-badge';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';
import {
  addProjectMilestone,
  getProject,
  linkProjectResource,
  updateProject,
  updateProjectMilestone,
} from '../../../../lib/workflow-client';
import { CanEdit, EditFieldset } from '../../../../lib/workspace-access';
import { label } from '../../../../lib/labels';

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuthenticatedUser();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [milestone, setMilestone] = useState('');
  const [resourceId, setResourceId] = useState('');
  const [resourceKind, setResourceKind] = useState<'tasks' | 'commands'>(
    'tasks',
  );
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!user) return;
    try {
      setProject(await getProject(id));
      setError('');
    } catch {
      setError('Não foi possível carregar este projeto.');
    }
  }, [id, user]);
  useEffect(() => void load(), [load]);

  async function changeStatus(status: ProjectStatus) {
    try {
      await updateProject(id, { status });
      await load();
    } catch {
      setError('Não foi possível atualizar o estado do projeto.');
    }
  }

  async function createMilestone(event: FormEvent) {
    event.preventDefault();
    try {
      await addProjectMilestone(id, { title: milestone });
      setMilestone('');
      await load();
    } catch {
      setError('Não foi possível adicionar o marco.');
    }
  }

  async function linkResource(event: FormEvent) {
    event.preventDefault();
    try {
      await linkProjectResource(id, resourceKind, resourceId);
      setResourceId('');
      await load();
    } catch {
      setError('Não foi possível ligar esse recurso do workspace.');
    }
  }

  if (authLoading || !user)
    return <main className="loading-page">A restaurar a sessão segura…</main>;
  if (!project)
    return (
      <main>
        <DashboardNav user={user} />
        <p className="empty-state">{error || 'Loading project…'}</p>
      </main>
    );

  return (
    <main>
      <DashboardNav user={user} />
      <div className="section-heading">
        <div>
          <Link href="/dashboard/projects">Projetos</Link>
          <h1 className="workflow-page-title">{project.name}</h1>
          <p>{project.description || 'Ainda sem descrição.'}</p>
        </div>
        <label>
          Estado
          <select
            value={project.status}
            onChange={(event) =>
              void changeStatus(event.target.value as ProjectStatus)
            }
          >
            {PROJECT_STATUSES.map((value) => (
              <option key={value} value={value}>
                {label(value)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && (
        <p className="form-message" role="alert">
          {error}
        </p>
      )}
      <section className="project-summary">
        <div>
          <span>Progresso</span>
          <strong>{project.progress_percentage}%</strong>
          <progress max="100" value={project.progress_percentage} />
        </div>
        <div>
          <span>Tarefas</span>
          <strong>
            {project.completed_task_count} / {project.task_count}
          </strong>
        </div>
        <div>
          <span>Prazo</span>
          <strong>
            {project.due_on
              ? new Date(`${project.due_on}T00:00:00`).toLocaleDateString(
                  'pt-PT',
                )
              : 'Não definido'}
          </strong>
        </div>
        <div>
          <span>Equipa</span>
          <strong>{project.members.length}</strong>
        </div>
      </section>
      <div className="project-detail-grid">
        <section>
          <h2>Marcos</h2>
          <CanEdit>
            <form className="inline-form" onSubmit={createMilestone}>
              <label>
                Novo marco
                <input
                  required
                  value={milestone}
                  onChange={(event) => setMilestone(event.target.value)}
                />
              </label>
              <button className="secondary-button">Adicionar</button>
            </form>
          </CanEdit>
          <EditFieldset>
            <div className="project-stack">
              {project.milestones.map((item) => (
                <article key={item.id}>
                  <button
                    className="status-toggle"
                    onClick={() =>
                      void updateProjectMilestone(id, item.id, {
                        status:
                          item.status === 'completed' ? 'pending' : 'completed',
                      }).then(load)
                    }
                    aria-label={`Mark ${item.title} ${item.status === 'completed' ? 'pending' : 'completed'}`}
                  >
                    {item.status === 'completed' ? '✓' : '○'}
                  </button>
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.due_on || 'Sem prazo'}</p>
                  </div>
                </article>
              ))}
            </div>
          </EditFieldset>
        </section>
        <section>
          <h2>Trabalho ligado</h2>
          <CanEdit>
            <form className="inline-form" onSubmit={linkResource}>
              <label>
                Recurso
                <select
                  value={resourceKind}
                  onChange={(event) =>
                    setResourceKind(event.target.value as 'tasks' | 'commands')
                  }
                >
                  <option value="tasks">Tarefa</option>
                  <option value="commands">Comando</option>
                </select>
              </label>
              <label>
                ID
                <input
                  required
                  value={resourceId}
                  onChange={(event) => setResourceId(event.target.value)}
                />
              </label>
              <button className="secondary-button">Ligar</button>
            </form>
          </CanEdit>
          <div className="project-stack">
            {project.tasks.map((task) => (
              <article key={task.id}>
                <div>
                  <Link href={`/dashboard/tasks/${task.id}`}>{task.title}</Link>
                  <p>{task.agent_id}</p>
                </div>
                <StatusBadge status={task.status} />
              </article>
            ))}
            {project.commands.map((command) => (
              <article key={command.id}>
                <div>
                  <Link href={`/dashboard/commands/${command.id}`}>
                    {command.input}
                  </Link>
                  <p>Comando</p>
                </div>
                <StatusBadge status={command.status} />
              </article>
            ))}
          </div>
        </section>
        <section>
          <h2>Equipa</h2>
          <div className="project-stack">
            {project.members.map((member) => (
              <article key={member.id}>
                <div>
                  <strong>{member.full_name}</strong>
                  <p>{member.email}</p>
                </div>
                <span>{label(member.role)}</span>
              </article>
            ))}
          </div>
        </section>
        <section>
          <h2>Atividade</h2>
          <ol className="project-activity">
            {project.activity.map((item) => (
              <li key={item.id}>
                <strong>{item.description}</strong>
                <time>{new Date(item.created_at).toLocaleString('pt-PT')}</time>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </main>
  );
}
