'use client';

import {
  RISK_LEVELS,
  TASK_PRIORITIES,
  TASK_TRANSITIONS,
  type AgentId,
  type RiskLevel,
  type TaskDetail,
  type TaskDependency,
  type TaskPriority,
  type TaskStatus,
  type WorkflowTask,
} from '@agent/shared';
import Link from 'next/link';
import { useParams } from '../../../../lib/route-params';
import { FormEvent, useCallback, useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { StatusBadge } from '../../../../components/status-badge';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';
import {
  createTaskDependency,
  deleteTaskDependency,
  getTask,
  listAgents,
  listTaskDependencies,
  listTasks,
  reassignTaskAgent,
  scheduleTask,
  transitionTask,
  updateTask,
  type Agent,
  WorkflowApiError,
} from '../../../../lib/workflow-client';
import { CanEdit, EditFieldset } from '../../../../lib/workspace-access';
import { label } from '../../../../lib/labels';

function localDateTime(value: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuthenticatedUser();
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [planTasks, setPlanTasks] = useState<WorkflowTask[]>([]);
  const [dependencies, setDependencies] = useState<TaskDependency[]>([]);
  const [dependencyTaskId, setDependencyTaskId] = useState('');
  const [title, setTitle] = useState('');
  const [instructions, setInstructions] = useState('');
  const [priority, setPriority] = useState<TaskPriority>('normal');
  const [risk, setRisk] = useState<RiskLevel>('green');
  const [agentId, setAgentId] = useState<AgentId>('supervisor');
  const [dueAt, setDueAt] = useState('');
  const [nextStatus, setNextStatus] = useState<TaskStatus | ''>('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const loadedTask = await getTask(id);
      const loadedAgents = await listAgents();
      const loadedPlanTasks = await listTasks(loadedTask.plan_id);
      const loadedDependencies = await listTaskDependencies(id);
      setTask(loadedTask);
      setAgents(loadedAgents);
      setPlanTasks(loadedPlanTasks);
      setDependencies(loadedDependencies);
      setTitle(loadedTask.title);
      setInstructions(loadedTask.instructions);
      setPriority(loadedTask.priority);
      setRisk(loadedTask.risk_level);
      setAgentId(loadedTask.agent_id);
      setDueAt(localDateTime(loadedTask.due_at));
      setNextStatus(TASK_TRANSITIONS[loadedTask.status][0] ?? '');
      const dependencyIds = new Set(
        loadedDependencies.map((item) => item.depends_on_task_id),
      );
      setDependencyTaskId(
        loadedPlanTasks.find(
          (item) => item.id !== id && !dependencyIds.has(item.id),
        )?.id ?? '',
      );
      setError('');
    } catch (loadError) {
      setError(
        loadError instanceof WorkflowApiError
          ? loadError.message
          : 'Não foi possível carregar esta tarefa.',
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (user) void load();
  }, [load, user]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!task) return;
    try {
      await updateTask(task.id, {
        title: title.trim(),
        instructions: instructions.trim(),
        priority,
        risk_level: risk,
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
      });
      if (agentId !== task.agent_id) await reassignTaskAgent(task.id, agentId);
      await load();
    } catch (saveError) {
      setError(
        saveError instanceof WorkflowApiError
          ? saveError.message
          : 'Não foi possível guardar a tarefa.',
      );
    }
  }

  async function transition() {
    if (!task || !nextStatus) return;
    try {
      await transitionTask(task.id, nextStatus, reason);
      setReason('');
      await load();
    } catch (transitionError) {
      setError(
        transitionError instanceof WorkflowApiError
          ? transitionError.message
          : 'Não foi possível alterar o estado.',
      );
    }
  }

  async function addDependency() {
    if (!task || !dependencyTaskId) return;
    try {
      await createTaskDependency(task.id, dependencyTaskId);
      await load();
    } catch (dependencyError) {
      setError(
        dependencyError instanceof WorkflowApiError
          ? dependencyError.message
          : 'Não foi possível adicionar a dependência.',
      );
    }
  }

  async function removeDependency(dependencyId: string) {
    if (!task) return;
    try {
      await deleteTaskDependency(task.id, dependencyId);
      await load();
    } catch (dependencyError) {
      setError(
        dependencyError instanceof WorkflowApiError
          ? dependencyError.message
          : 'Não foi possível remover a dependência.',
      );
    }
  }

  async function schedule() {
    if (!task) return;
    try {
      await scheduleTask(task.id);
      await load();
    } catch (scheduleError) {
      setError(
        scheduleError instanceof WorkflowApiError
          ? scheduleError.message
          : 'Não foi possível avaliar esta tarefa.',
      );
    }
  }

  if (authLoading || !user || loading)
    return <main className="loading-page">A carregar a tarefa…</main>;

  return (
    <main>
      <DashboardNav user={user} />
      {error && (
        <p className="form-message" role="alert">
          {error}
        </p>
      )}
      {task ? (
        <>
          <section className="workflow-panel">
            <div className="workflow-panel__heading">
              <div>
                <p className="eyebrow">Tarefa · {task.plan_title}</p>
                <h1>{task.title}</h1>
              </div>
              <StatusBadge status={task.status} />
            </div>
            <Link href={`/dashboard/commands/${task.command_id}`}>
              Ver o comando de origem: {task.command_input}
            </Link>
          </section>
          <section className="workflow-panel workflow-form-panel">
            <h2>Definições da tarefa</h2>
            <EditFieldset>
              <form
                className="workflow-form workflow-form--grid"
                onSubmit={save}
              >
                <label>
                  Título
                  <input
                    required
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                  />
                </label>
                <label>
                  Agente
                  <select
                    value={agentId}
                    onChange={(event) =>
                      setAgentId(event.target.value as AgentId)
                    }
                  >
                    {agents.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Prioridade
                  <select
                    value={priority}
                    onChange={(event) =>
                      setPriority(event.target.value as TaskPriority)
                    }
                  >
                    {TASK_PRIORITIES.map((value) => (
                      <option key={value} value={value}>
                        {label(value)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Risco
                  <select
                    value={risk}
                    onChange={(event) =>
                      setRisk(event.target.value as RiskLevel)
                    }
                  >
                    {RISK_LEVELS.map((value) => (
                      <option key={value} value={value}>
                        {label(value)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Prazo
                  <input
                    type="datetime-local"
                    value={dueAt}
                    onChange={(event) => setDueAt(event.target.value)}
                  />
                </label>
                <label className="workflow-form__wide">
                  Instruções
                  <textarea
                    required
                    rows={5}
                    value={instructions}
                    onChange={(event) => setInstructions(event.target.value)}
                  />
                </label>
                <button className="primary-button" type="submit">
                  Guardar tarefa
                </button>
              </form>
            </EditFieldset>
          </section>
          <CanEdit>
            {TASK_TRANSITIONS[task.status].length > 0 && (
              <section className="workflow-panel">
                <h2>Alterar estado</h2>
                <div className="task-transition-controls">
                  <select
                    aria-label="Próximo estado"
                    value={nextStatus}
                    onChange={(event) =>
                      setNextStatus(event.target.value as TaskStatus)
                    }
                  >
                    {TASK_TRANSITIONS[task.status].map((value) => (
                      <option key={value} value={value}>
                        {label(value)}
                      </option>
                    ))}
                  </select>
                  <input
                    aria-label="Motivo da mudança"
                    value={reason}
                    maxLength={2000}
                    placeholder="Motivo (opcional)"
                    onChange={(event) => setReason(event.target.value)}
                  />
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => void transition()}
                  >
                    Atualizar estado
                  </button>
                </div>
              </section>
            )}
          </CanEdit>
          <section className="workflow-panel">
            <div className="workflow-panel__heading">
              <div>
                <p className="eyebrow">Grafo do plano</p>
                <h2>Dependências</h2>
              </div>
              <CanEdit>
                {(task.status === 'ready' || task.status === 'blocked') && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => void schedule()}
                  >
                    Avaliar agendamento
                  </button>
                )}
              </CanEdit>
            </div>
            {dependencies.length === 0 ? (
              <p className="empty-state">Sem dependências configuradas.</p>
            ) : (
              <ul className="task-dependencies">
                {dependencies.map((dependency) => {
                  const dependencyTask = planTasks.find(
                    (item) => item.id === dependency.depends_on_task_id,
                  );
                  return (
                    <li key={dependency.id}>
                      <Link
                        href={`/dashboard/tasks/${dependency.depends_on_task_id}`}
                      >
                        {dependencyTask?.title ?? 'Tarefa do plano'}
                      </Link>
                      <StatusBadge
                        status={dependencyTask?.status ?? 'pending'}
                      />
                      <CanEdit>
                        <button
                          type="button"
                          onClick={() => void removeDependency(dependency.id)}
                        >
                          Remover
                        </button>
                      </CanEdit>
                    </li>
                  );
                })}
              </ul>
            )}
            <CanEdit>
              {planTasks.some(
                (item) =>
                  item.id !== task.id &&
                  !dependencies.some(
                    (dependency) => dependency.depends_on_task_id === item.id,
                  ),
              ) && (
                <div className="dependency-add-controls">
                  <select
                    aria-label="Tarefa de que depende"
                    value={dependencyTaskId}
                    onChange={(event) =>
                      setDependencyTaskId(event.target.value)
                    }
                  >
                    {planTasks
                      .filter(
                        (item) =>
                          item.id !== task.id &&
                          !dependencies.some(
                            (dependency) =>
                              dependency.depends_on_task_id === item.id,
                          ),
                      )
                      .map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.title}
                        </option>
                      ))}
                  </select>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={!dependencyTaskId}
                    onClick={() => void addDependency()}
                  >
                    Adicionar dependência
                  </button>
                </div>
              )}
            </CanEdit>
          </section>
          <section className="workflow-panel">
            <h2>Histórico</h2>
            <ol className="task-history">
              {task.history.map((item) => (
                <li key={item.id}>
                  <StatusBadge status={item.to_status} />
                  <span>
                    {new Date(item.created_at).toLocaleString('pt-PT')}
                  </span>
                  {item.reason && <p>{item.reason}</p>}
                </li>
              ))}
            </ol>
          </section>
        </>
      ) : (
        <p className="empty-state">Tarefa indisponível.</p>
      )}
    </main>
  );
}
