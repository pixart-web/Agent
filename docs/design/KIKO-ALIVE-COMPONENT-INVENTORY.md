# Kiko Alive — Component inventory

All components are in `apps/web/components/kiko/` unless noted. Styles: `app/kiko-alive.css`.

| Requested component | Implementation                                    | Notes                                                                                   |
| ------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------------- |
| KikoAppShell        | `components/dashboard-nav.tsx` → `DashboardNav`   | Keeps the old name so all 30+ pages use it unchanged; rail + top bar + drawer + palette |
| KikoNavigation      | `DashboardNav` (`PRIMARY_NAV`, `MORE_NAV`)        | Collapsible, responsive, `aria-current`                                                 |
| KikoHero            | `kiko-home.tsx` (`.kiko-hero` section)            | Greeting, character, live status                                                        |
| KikoAvatar          | `kiko-avatar.tsx`                                 | SVG + CSS, 10 states, `decorative` mode                                                 |
| KikoCommandBar      | `kiko-home.tsx` → `KikoCommandBar`                | Starts a conversation; reports listening/thinking/outcome                               |
| KikoQuickActions    | `kiko-home.tsx` → `QUICK_ACTIONS`                 | Links to existing workflows (tested)                                                    |
| KikoAgentCard       | `kiko-ui.tsx` → `KikoAgentList`, `agentActivity`  | One row per specialist from `GET /agents/{id}/overview`                                 |
| KikoExecutionCard   | `kiko-ui.tsx` → `KikoExecutionCard`               | Real plan progress (`KikoProgressRing`)                                                 |
| KikoActivityFeed    | `kiko-ui.tsx` → `KikoActivityFeed`                | Notifications + executions (`buildActivity`)                                            |
| KikoContextPanel    | `kiko-context-panel.tsx`                          | `docked` (home) or `drawer` (elsewhere)                                                 |
| KikoWorkspace       | `kiko-workspace.tsx` → `KikoWorkspaceMode`        | Planning / execution / analysis / conversation; `commandStage()`                        |
| KikoStatusIndicator | `kiko-ui.tsx`                                     | Text + dot, `role="status"`                                                             |
| KikoApprovalPanel   | `kiko-ui.tsx`                                     | Only rendered when approvals are pending                                                |
| KikoEmptyState      | `kiko-ui.tsx`                                     |                                                                                         |
| KikoLoadingState    | `kiko-ui.tsx`                                     | Skeleton bars; shimmer off with reduced motion                                          |
| KikoErrorState      | `kiko-ui.tsx`                                     | Adds the local-AI recovery hint (`lib/ai-errors.ts`)                                    |
| —                   | `kiko-ui.tsx` → `KikoSection`, `KikoProgressRing` | Card frame; progress ring                                                               |
| —                   | `kiko-icons.tsx` → `KikoIcon`                     | Icon set                                                                                |
| —                   | `kiko-home.tsx` → `KikoEcosystem`                 | Integration states                                                                      |

## Data and logic

| Module                                                 | Purpose                                                                              |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| `lib/kiko-state.ts`                                    | State machine `deriveKikoState`, state copy, greeting                                |
| `lib/use-kiko-signals.ts`                              | Shared poll: health, operations overview, AI availability, planning count; idle time |
| `lib/use-kiko-activity.ts`                             | Commands in progress with plan progress, notifications, feed helpers                 |
| `lib/workspace-settings-client.ts` → `switchWorkspace` | Workspace switcher                                                                   |
| `components/desktop-shell.tsx`                         | Exports `CommandPalette` and `PALETTE_EVENT` for the shell's search                  |

## Migration map (existing screens)

| Area                                   | Change                                             |
| -------------------------------------- | -------------------------------------------------- |
| All dashboard pages                    | New shell (via `DashboardNav`), dark tokens        |
| `/dashboard`                           | Replaced by `KikoHome`                             |
| `/dashboard/commands/[id]`             | `KikoWorkspaceMode` header + existing panels       |
| `/dashboard/kiko/[id]`                 | Conversation mode header (`conversationStage`)     |
| `/dashboard/analytics`                 | Analysis mode header                               |
| Status badges, alerts, approval cards  | Recoloured for dark surfaces                       |
| Buttons, inputs, selects               | Kiko Alive controls (amber primary with dark text) |
| Auth pages, onboarding, public landing | Inherit tokens; not redesigned in this pass        |

## Tests

`tests/kiko-alive.test.tsx` (state machine, avatar states and labels, status text, progress,
activity feed, agent activity, command stages, workspace header) and
`tests/kiko-shell.test.ts` (all modules reachable, current-page logic, quick actions).
