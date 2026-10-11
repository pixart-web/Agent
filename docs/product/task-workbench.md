# Task Workbench

The workspace task workbench exposes the governed task graph outside an individual command.

## Product behavior

- `/dashboard/tasks` lists tasks in the active workspace and supports bounded search plus status, priority, and agent filters.
- Search covers task titles, task instructions, and the parent command input.
- Every row links to a standalone task detail while retaining a link back to its parent command.
- The detail view supports task copy, priority, risk, deadline, and explicit agent assignment updates.
- Status changes continue to use the existing transition state machine and persist a reasoned history.
- Deadlines are optional and can be cleared. They do not automatically execute or reschedule work.

## Governance and isolation

- Task reads and writes traverse task → plan → command and enforce the active workspace boundary.
- Agent reassignment uses the existing explicit reassignment service and its execution-state guards.
- The workbench does not duplicate plans, task history, execution state, or audit records.
- List requests are capped at 100 records and all filter input is validated at the API boundary.

## Remaining scope

Dependency editing, scheduling controls, board/Kanban presentation, and a general project aggregate remain subsequent roadmap increments.
