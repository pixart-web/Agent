'use client';

import {
  PROJECT_STATUSES,
  type Project,
  type ProjectStatus,
} from '@agent/shared';
import Link from 'next/link';
import { FormEvent, useCallback, useEffect, useState } from 'react';

import { DashboardNav } from '../../../components/dashboard-nav';
import { StatusBadge } from '../../../components/status-badge';
import { useAuthenticatedUser } from '../../../lib/use-authenticated-user';
import { createProject, listProjects } from '../../../lib/workflow-client';

export default function ProjectsPage() {
  const { user, loading: authLoading } = useAuthenticatedUser();
  const [projects, setProjects] = useState<Project[]>([]);
  const [status, setStatus] = useState<ProjectStatus | ''>('');
  const [search, setSearch] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [dueOn, setDueOn] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      setProjects(
        await listProjects({
          status: status || undefined,
          search: search || undefined,
        }),
      );
      setError('');
    } catch {
      setError('Unable to load projects right now.');
    } finally {
      setLoading(false);
    }
  }, [search, status, user]);

  useEffect(() => void load(), [load]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      await createProject({
        name,
        description: description || undefined,
        due_on: dueOn || undefined,
      });
      setName('');
      setDescription('');
      setDueOn('');
      await load();
    } catch {
      setError(
        'The project could not be created. Check the details and retry.',
      );
    } finally {
      setSaving(false);
    }
  }

  if (authLoading || !user)
    return <main className="loading-page">Restoring your secure session…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      <div className="section-heading">
        <div>
          <p className="eyebrow">Workspace delivery</p>
          <h1 className="workflow-page-title">Projects</h1>
        </div>
        <span>{projects.length} visible</span>
      </div>
      <div className="project-layout">
        <section>
          <div className="task-filters">
            <label>
              Search
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Name or description"
              />
            </label>
            <label>
              Status
              <select
                value={status}
                onChange={(event) =>
                  setStatus(event.target.value as ProjectStatus | '')
                }
              >
                <option value="">All</option>
                {PROJECT_STATUSES.map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </label>
          </div>
          {error && (
            <p className="form-message" role="alert">
              {error}
            </p>
          )}
          {loading ? (
            <p>Loading projects…</p>
          ) : projects.length === 0 ? (
            <p className="empty-state">
              No projects yet. Create the first delivery workspace alongside.
            </p>
          ) : (
            <div className="project-list">
              {projects.map((project) => (
                <Link
                  href={`/dashboard/projects/${project.id}`}
                  className="project-row"
                  key={project.id}
                >
                  <div>
                    <strong>{project.name}</strong>
                    <p>{project.description || 'No description'}</p>
                  </div>
                  <div className="project-progress">
                    <span>
                      {project.completed_task_count}/{project.task_count} tasks
                    </span>
                    <progress max="100" value={project.progress_percentage} />
                  </div>
                  <span>
                    {project.due_on
                      ? new Date(
                          `${project.due_on}T00:00:00`,
                        ).toLocaleDateString()
                      : 'No deadline'}
                  </span>
                  <StatusBadge status={project.status} />
                </Link>
              ))}
            </div>
          )}
        </section>
        <form className="project-create" onSubmit={submit}>
          <h2>New project</h2>
          <label>
            Name
            <input
              required
              maxLength={255}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label>
            Description
            <textarea
              maxLength={10000}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
          <label>
            Deadline
            <input
              type="date"
              value={dueOn}
              onChange={(event) => setDueOn(event.target.value)}
            />
          </label>
          <button className="primary-button" disabled={saving}>
            {saving ? 'Creating…' : 'Create project'}
          </button>
        </form>
      </div>
    </main>
  );
}
