'use client';

import {
  RISK_LEVELS,
  TASK_PRIORITIES,
  TASK_TRANSITIONS,
  type AgentId,
  type RiskLevel,
  type TaskDetail,
  type TaskPriority,
  type TaskStatus,
} from '@agent/shared';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { FormEvent, useCallback, useEffect, useState } from 'react';

import { DashboardNav } from '../../../../components/dashboard-nav';
import { StatusBadge } from '../../../../components/status-badge';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';
import {
  getTask,
  listAgents,
  reassignTaskAgent,
  transitionTask,
  updateTask,
  type Agent,
  WorkflowApiError,
} from '../../../../lib/workflow-client';

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
      const [loadedTask, loadedAgents] = await Promise.all([
        getTask(id),
        listAgents(),
      ]);
      setTask(loadedTask);
      setAgents(loadedAgents);
      setTitle(loadedTask.title);
      setInstructions(loadedTask.instructions);
      setPriority(loadedTask.priority);
      setRisk(loadedTask.risk_level);
      setAgentId(loadedTask.agent_id);
      setDueAt(localDateTime(loadedTask.due_at));
      setNextStatus(TASK_TRANSITIONS[loadedTask.status][0] ?? '');
      setError('');
    } catch (loadError) {
      setError(
        loadError instanceof WorkflowApiError
          ? loadError.message
          : 'Unable to load this task.',
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
          : 'Unable to save the task.',
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
          : 'Unable to change status.',
      );
    }
  }

  if (authLoading || !user || loading)
    return <main className="loading-page">Loading task…</main>;

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
                <p className="eyebrow">Task · {task.plan_title}</p>
                <h1>{task.title}</h1>
              </div>
              <StatusBadge status={task.status} />
            </div>
            <Link href={`/dashboard/commands/${task.command_id}`}>
              View parent command: {task.command_input}
            </Link>
          </section>
          <section className="workflow-panel workflow-form-panel">
            <h2>Task settings</h2>
            <form className="workflow-form workflow-form--grid" onSubmit={save}>
              <label>
                Title
                <input
                  required
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                />
              </label>
              <label>
                Agent
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
                Priority
                <select
                  value={priority}
                  onChange={(event) =>
                    setPriority(event.target.value as TaskPriority)
                  }
                >
                  {TASK_PRIORITIES.map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
              <label>
                Risk
                <select
                  value={risk}
                  onChange={(event) => setRisk(event.target.value as RiskLevel)}
                >
                  {RISK_LEVELS.map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
              <label>
                Deadline
                <input
                  type="datetime-local"
                  value={dueAt}
                  onChange={(event) => setDueAt(event.target.value)}
                />
              </label>
              <label className="workflow-form__wide">
                Instructions
                <textarea
                  required
                  rows={5}
                  value={instructions}
                  onChange={(event) => setInstructions(event.target.value)}
                />
              </label>
              <button className="primary-button" type="submit">
                Save task
              </button>
            </form>
          </section>
          {TASK_TRANSITIONS[task.status].length > 0 && (
            <section className="workflow-panel">
              <h2>Change status</h2>
              <div className="task-transition-controls">
                <select
                  aria-label="Next status"
                  value={nextStatus}
                  onChange={(event) =>
                    setNextStatus(event.target.value as TaskStatus)
                  }
                >
                  {TASK_TRANSITIONS[task.status].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
                <input
                  aria-label="Transition reason"
                  value={reason}
                  maxLength={2000}
                  placeholder="Reason (optional)"
                  onChange={(event) => setReason(event.target.value)}
                />
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => void transition()}
                >
                  Update status
                </button>
              </div>
            </section>
          )}
          <section className="workflow-panel">
            <h2>History</h2>
            <ol className="task-history">
              {task.history.map((item) => (
                <li key={item.id}>
                  <StatusBadge status={item.to_status} />
                  <span>{new Date(item.created_at).toLocaleString()}</span>
                  {item.reason && <p>{item.reason}</p>}
                </li>
              ))}
            </ol>
          </section>
        </>
      ) : (
        <p className="empty-state">Task unavailable.</p>
      )}
    </main>
  );
}
