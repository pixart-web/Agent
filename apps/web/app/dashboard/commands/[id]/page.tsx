'use client';

import {
  RISK_LEVELS,
  TASK_PRIORITIES,
  TASK_TRANSITIONS,
  type AgentId,
  type Command,
  type Plan,
  type RiskLevel,
  type SupervisorRun,
  type TaskDetail,
  type TaskPriority,
  type TaskStatus,
} from '@agent/shared';
import { useParams } from 'next/navigation';
import { FormEvent, useCallback, useEffect, useState } from 'react';

import { CommandDetail } from '../../../../components/command-detail';
import { DashboardNav } from '../../../../components/dashboard-nav';
import { SupervisorPlanReview } from '../../../../components/supervisor-plan-review';
import { TaskExecutionPanel } from '../../../../components/task-execution-panel';
import { useAuthenticatedUser } from '../../../../lib/use-authenticated-user';
import {
  approvePlan,
  cancelCommand,
  createPlan,
  createTask,
  generateSupervisorPlan,
  getCommand,
  getTask,
  listAgents,
  listPlans,
  listSupervisorRuns,
  listTasks,
  regenerateSupervisorPlan,
  transitionTask,
  type Agent,
  WorkflowApiError,
} from '../../../../lib/workflow-client';

export default function CommandDetailPage() {
  const { id: commandId } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuthenticatedUser();
  const [command, setCommand] = useState<Command | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [planVersions, setPlanVersions] = useState<Plan[]>([]);
  const [supervisorRun, setSupervisorRun] = useState<SupervisorRun | null>(
    null,
  );
  const [supervisorPlanning, setSupervisorPlanning] = useState(false);
  const [supervisorError, setSupervisorError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [tasks, setTasks] = useState<TaskDetail[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [planTitle, setPlanTitle] = useState('');
  const [planObjective, setPlanObjective] = useState('');
  const [taskTitle, setTaskTitle] = useState('');
  const [taskInstructions, setTaskInstructions] = useState('');
  const [agentId, setAgentId] = useState<AgentId>('supervisor');
  const [priority, setPriority] = useState<TaskPriority>('normal');
  const [riskLevel, setRiskLevel] = useState<RiskLevel>('green');
  const [sequence, setSequence] = useState(1);
  const [transitionStatus, setTransitionStatus] = useState<
    Record<string, TaskStatus>
  >({});
  const [transitionReason, setTransitionReason] = useState<
    Record<string, string>
  >({});

  const loadWorkflow = useCallback(async () => {
    setError('');
    try {
      const [loadedCommand, loadedAgents] = await Promise.all([
        getCommand(commandId),
        listAgents(),
      ]);
      const [versions, runs] = await Promise.all([
        listPlans(commandId),
        listSupervisorRuns(commandId),
      ]);
      const loadedPlan = versions.find((item) => item.is_current) ?? null;
      let loadedTasks: TaskDetail[] = [];
      if (loadedPlan) {
        const taskList = await listTasks(loadedPlan.id);
        loadedTasks = await Promise.all(
          taskList.map((task) => getTask(task.id)),
        );
      }
      setCommand(loadedCommand);
      setAgents(loadedAgents);
      setPlan(loadedPlan);
      setPlanVersions(versions);
      setSupervisorRun(
        runs.find((run) => run.status === 'completed') ?? runs[0] ?? null,
      );
      setTasks(loadedTasks);
      if (loadedAgents[0]) setAgentId(loadedAgents[0].id);
    } catch (loadError) {
      setError(
        loadError instanceof WorkflowApiError
          ? loadError.message
          : 'Unable to load this workflow.',
      );
    } finally {
      setLoading(false);
    }
  }, [commandId]);

  useEffect(() => {
    if (user) void loadWorkflow();
  }, [loadWorkflow, user]);

  async function handlePlanSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await createPlan(commandId, {
        title: planTitle.trim(),
        objective: planObjective.trim(),
      });
      setPlanTitle('');
      setPlanObjective('');
      await loadWorkflow();
    } catch (submitError) {
      setError(
        submitError instanceof WorkflowApiError
          ? submitError.message
          : 'Unable to create the plan.',
      );
    }
  }

  async function handleGeneratePlan() {
    setSupervisorPlanning(true);
    setSupervisorError('');
    try {
      await generateSupervisorPlan(commandId);
      await loadWorkflow();
    } catch (generateError) {
      setSupervisorError(
        generateError instanceof WorkflowApiError
          ? generateError.message
          : 'Não foi possível gerar o plano. Tenta novamente.',
      );
    } finally {
      setSupervisorPlanning(false);
    }
  }

  async function handleApprovePlan() {
    if (!plan) return;
    setSupervisorPlanning(true);
    setSupervisorError('');
    try {
      await approvePlan(plan.id);
      await loadWorkflow();
    } catch (approveError) {
      setSupervisorError(
        approveError instanceof WorkflowApiError
          ? approveError.message
          : 'Não foi possível aprovar o plano.',
      );
    } finally {
      setSupervisorPlanning(false);
    }
  }

  async function handleRegeneratePlan() {
    if (!feedback.trim()) return;
    setSupervisorPlanning(true);
    setSupervisorError('');
    try {
      await regenerateSupervisorPlan(commandId, feedback.trim());
      setFeedback('');
      await loadWorkflow();
    } catch (regenerateError) {
      setSupervisorError(
        regenerateError instanceof WorkflowApiError
          ? regenerateError.message
          : 'Não foi possível rever o plano.',
      );
    } finally {
      setSupervisorPlanning(false);
    }
  }

  async function handleTaskSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!plan) return;
    try {
      await createTask(plan.id, {
        agent_id: agentId,
        title: taskTitle.trim(),
        instructions: taskInstructions.trim(),
        priority,
        risk_level: riskLevel,
        sequence,
      });
      setTaskTitle('');
      setTaskInstructions('');
      setSequence(tasks.length + 2);
      await loadWorkflow();
    } catch (submitError) {
      setError(
        submitError instanceof WorkflowApiError
          ? submitError.message
          : 'Unable to create the task.',
      );
    }
  }

  async function handleTransition(task: TaskDetail) {
    const nextStatus =
      transitionStatus[task.id] ?? TASK_TRANSITIONS[task.status][0];
    if (!nextStatus) return;
    try {
      await transitionTask(task.id, nextStatus, transitionReason[task.id]);
      await loadWorkflow();
    } catch (transitionError) {
      setError(
        transitionError instanceof WorkflowApiError
          ? transitionError.message
          : 'Unable to change task status.',
      );
    }
  }

  async function handleCancelCommand() {
    try {
      await cancelCommand(commandId);
      await loadWorkflow();
    } catch (cancelError) {
      setError(
        cancelError instanceof WorkflowApiError
          ? cancelError.message
          : 'Unable to cancel the command.',
      );
    }
  }

  if (authLoading || !user || loading) {
    return <main className="loading-page">Loading workflow…</main>;
  }

  return (
    <main>
      <DashboardNav user={user} />
      {error && (
        <p className="form-message workflow-alert" role="alert">
          {error}
        </p>
      )}
      {command ? (
        <>
          <CommandDetail
            command={command}
            plan={null}
            tasks={[]}
            agents={agents}
            statusLabel={
              command.status === 'planning'
                ? plan
                  ? 'Waiting for approval'
                  : 'Supervisor planning'
                : undefined
            }
          />
          <SupervisorPlanReview
            plan={plan}
            tasks={tasks}
            versions={planVersions}
            run={supervisorRun}
            agents={agents}
            planning={supervisorPlanning}
            error={supervisorError}
            feedback={feedback}
            onFeedbackChange={setFeedback}
            onGenerate={() => void handleGeneratePlan()}
            onApprove={() => void handleApprovePlan()}
            onRegenerate={() => void handleRegeneratePlan()}
          />
          {plan?.status !== 'draft' && tasks.length > 0 && (
            <TaskExecutionPanel commandId={commandId} tasks={tasks} />
          )}
          {!['completed', 'cancelled'].includes(command.status) && (
            <button
              className="danger-button"
              type="button"
              onClick={handleCancelCommand}
            >
              Cancel command
            </button>
          )}
        </>
      ) : (
        <p className="empty-state">Command unavailable.</p>
      )}

      {command && !plan && (
        <details className="workflow-panel workflow-form-panel">
          <summary>Create a plan manually</summary>
          <form className="workflow-form" onSubmit={handlePlanSubmit}>
            <label>
              Title
              <input
                required
                value={planTitle}
                onChange={(event) => setPlanTitle(event.target.value)}
              />
            </label>
            <label>
              Objective
              <textarea
                required
                rows={5}
                value={planObjective}
                onChange={(event) => setPlanObjective(event.target.value)}
              />
            </label>
            <button className="primary-button" type="submit">
              Create plan
            </button>
          </form>
        </details>
      )}

      {plan?.status === 'draft' && (
        <section className="workflow-panel workflow-form-panel">
          <h2>Add a task</h2>
          <form
            className="workflow-form workflow-form--grid"
            onSubmit={handleTaskSubmit}
          >
            <label>
              Title
              <input
                required
                value={taskTitle}
                onChange={(event) => setTaskTitle(event.target.value)}
              />
            </label>
            <label>
              Agent
              <select
                value={agentId}
                onChange={(event) => setAgentId(event.target.value as AgentId)}
              >
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="workflow-form__wide">
              Instructions
              <textarea
                required
                rows={5}
                value={taskInstructions}
                onChange={(event) => setTaskInstructions(event.target.value)}
              />
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
                value={riskLevel}
                onChange={(event) =>
                  setRiskLevel(event.target.value as RiskLevel)
                }
              >
                {RISK_LEVELS.map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </label>
            <label>
              Sequence
              <input
                type="number"
                min={1}
                value={sequence}
                onChange={(event) => setSequence(Number(event.target.value))}
              />
            </label>
            <button className="primary-button" type="submit">
              Add task
            </button>
          </form>
        </section>
      )}

      {tasks.map((task) => {
        const transitions = TASK_TRANSITIONS[task.status];
        return (
          <section className="task-control" key={`control-${task.id}`}>
            <div>
              <strong>{task.title}</strong>
              <span>{task.history.length} status changes</span>
            </div>
            {transitions.length > 0 && (
              <div className="task-control__actions">
                <select
                  aria-label={`Next status for ${task.title}`}
                  value={transitionStatus[task.id] ?? transitions[0]}
                  onChange={(event) =>
                    setTransitionStatus((current) => ({
                      ...current,
                      [task.id]: event.target.value as TaskStatus,
                    }))
                  }
                >
                  {transitions.map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
                <input
                  aria-label={`Reason for ${task.title}`}
                  placeholder="Reason (optional)"
                  value={transitionReason[task.id] ?? ''}
                  onChange={(event) =>
                    setTransitionReason((current) => ({
                      ...current,
                      [task.id]: event.target.value,
                    }))
                  }
                />
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => handleTransition(task)}
                >
                  Change status
                </button>
              </div>
            )}
            <details>
              <summary>Status history</summary>
              <ol className="history-list">
                {task.history.map((entry) => (
                  <li key={entry.id}>
                    {entry.from_status ?? 'created'} → {entry.to_status}
                    {entry.reason ? ` — ${entry.reason}` : ''}
                  </li>
                ))}
              </ol>
            </details>
          </section>
        );
      })}
    </main>
  );
}
