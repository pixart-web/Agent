import type { Command, Plan, WorkflowTask } from '@agent/shared';
import React from 'react';

import type { Agent } from '../lib/workflow-client';
import { StatusBadge } from './status-badge';

export function CommandDetail({
  command,
  plan,
  tasks,
  agents,
  statusLabel,
}: {
  command: Command;
  plan: Plan | null;
  tasks: WorkflowTask[];
  agents: Agent[];
  statusLabel?: string;
}) {
  const agentNames = Object.fromEntries(
    agents.map((agent) => [agent.id, agent.name]),
  );

  return (
    <>
      <section className="workflow-panel">
        <div className="workflow-panel__heading">
          <p className="eyebrow">Command</p>
          <StatusBadge status={command.status} label={statusLabel} />
        </div>
        <h1 className="workflow-title">{command.input}</h1>
      </section>

      {plan && (
        <section className="workflow-panel">
          <div className="workflow-panel__heading">
            <div>
              <p className="eyebrow">Plan</p>
              <h2>{plan.title}</h2>
            </div>
            <StatusBadge status={plan.status} />
          </div>
          <p>{plan.objective}</p>
        </section>
      )}

      {tasks.length > 0 && (
        <section aria-labelledby="task-list-title">
          <div className="section-heading">
            <h2 id="task-list-title">Tasks</h2>
            <span>{tasks.length} configured</span>
          </div>
          <div className="task-list">
            {tasks.map((task) => (
              <article className="task-card" key={task.id}>
                <div className="workflow-panel__heading">
                  <span className="task-sequence">#{task.sequence}</span>
                  <StatusBadge status={task.status} />
                </div>
                <h3>{task.title}</h3>
                <p>{task.instructions}</p>
                <dl className="task-meta">
                  <div>
                    <dt>Agent</dt>
                    <dd>{agentNames[task.agent_id] ?? task.agent_id}</dd>
                  </div>
                  <div>
                    <dt>Priority</dt>
                    <dd>{task.priority}</dd>
                  </div>
                  <div>
                    <dt>Risk</dt>
                    <dd>{task.risk_level}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
