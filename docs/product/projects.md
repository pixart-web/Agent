# Projects

Projects are workspace-scoped delivery containers that connect business intent to Kiko's existing command and task execution graph.

## Capabilities

- Create, search, filter, inspect, and update projects.
- Track planned, active, blocked, completed, and cancelled states.
- Set descriptions, start dates, deadlines, owners, members, and optional CRM clients.
- Create and complete milestones.
- Link workspace tasks and commands without duplicating workflow state.
- Calculate progress from linked task completion.
- Review a persisted project activity trail.

All reads and writes are constrained by the authenticated user's active workspace. A task, command, client, or member from another workspace cannot be linked. The project owner is enrolled automatically and cannot be removed.

## API

The authenticated API is exposed below `/api/v1/projects`. It includes project list/create/detail/update, member management, milestone management, and task/command link management. Duplicate links return `409`; absent or cross-tenant resources return `404`.

## Product behavior

The Projects navigation entry opens the workspace list and creation form. Project detail shows real task-derived progress, milestones, team, linked work, and the latest 100 activity events. Linking work requires the UUID of an existing workspace task or command; a richer picker can be layered over the same API without changing the domain contract.
