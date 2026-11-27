# Kiko Alive — Implementation report

**Branch:** `feature/kiko-alive-ui` (from `main` at `866784d`). **Build:** Kiko for macOS 0.3.0.
**Status:** ready for the comprehensive QA program; not a claim of full QA completion.

## What was delivered

- Dark Kiko Alive theme applied to every screen through the existing token names.
- Original Kiko character (SVG + CSS) with 10 states driven only by real application data.
- New shell: collapsible navigation rail with every module, ⌘K search, workspace switcher,
  activity drawer, responsive layouts (desktop, laptop, phone width).
- New home: greeting, hero with live status, natural-language request box (starts a Kiko
  conversation), quick actions, real executions, agents, activity and integration states.
- Adaptive workspace headers: planning/execution (commands), conversation, analysis.
- Design documents: design system, UX specification, component inventory, this report.

No backend, API, permission or data-model changes. No new dependencies (runtime or AI).

## Decisions

| Decision                                             | Reason                                                                                                                                                                             |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SVG + CSS character, not 3D/Rive                     | Cheapest option meeting the bar; no GPU scene, no runtime, works offline in the WebView; the static frame is the fallback. A 3D/Rive version can replace it behind the same props. |
| Shell implemented inside `DashboardNav`              | All 30+ pages already render it first in `<main>`; one change moves every page to the new shell with no per-page edits or broken routes.                                           |
| Request box opens a Kiko conversation                | The conversation workflow already turns a request into a command and plan with the local AI; no new endpoint.                                                                      |
| No microphone, attachments, WordPress/database tiles | Not implemented in the product; the brief forbids non-functional controls and implied integrations.                                                                                |
| Shell and home in European Portuguese                | Matches the owner's reference design; module screens are still in English (follow-up).                                                                                             |
| "Log out" became "Terminar sessão"                   | Portuguese shell; the desktop journey was updated accordingly.                                                                                                                     |

## Verification (all executed on 2026-11-20)

| Check                                                                                                                                                                                                                        | Result                                                                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Web unit/component tests (Vitest)                                                                                                                                                                                            | 96 / 96 passed (18 new: state machine, avatar, navigation coverage, stages)                                   |
| TypeScript, ESLint                                                                                                                                                                                                           | Clean                                                                                                         |
| Authenticated quality sweep, 21 dashboard routes × desktop + phone (page errors, API ≥ 500, horizontal overflow, axe WCAG 2 A/AA serious/critical)                                                                           | No findings. A first run timed out on the dev server's first compilation of the new pages; the re-run passed. |
| Desktop journey (debug build with the new UI, real local model): register, verify, onboarding, AI plan, approval, governed action executed by the worker, project, conversation, CRM, relaunch with Keychain session, logout | All phases passed                                                                                             |
| Keyboard                                                                                                                                                                                                                     | First Tab reaches the skip link; ⌘K opens search; Escape closes drawer/palette                                |
| Reduced motion                                                                                                                                                                                                               | Character static, rings static, no transitions; idle main-thread time 0.01 %                                  |

## Performance

Browser measurements (Chromium via CDP, local dev server, 1440 × 900, owner account with real data):

| Metric                                 | Motion on | Reduced motion |
| -------------------------------------- | --------- | -------------- |
| Home: character visible after reload   | 310 ms    | 306 ms         |
| Home: live agent/execution data shown  | 493 ms    | 485 ms         |
| Idle main-thread time (10 s window)    | 0.28 %    | 0.01 %         |
| JS heap after load                     | 22.4 MB   | 17.3 MB        |
| Navigation (rail click → page heading) | 31–42 ms  | 43–200 ms*     |

\* One 200 ms sample returning to the home page while its data reloaded.

Installed app (0.3.0, release build, idle on the home page, 30 s sampling): main process
0.0 % CPU, 101 MB RSS. The dev-server figures above are upper bounds; the release bundle is
pre-compiled. Not measured: cold-start time of the packaged app (no instrumentation in the
app for first paint), animation frame timing on low-end hardware, behaviour with the local
AI saturated beyond the existing background-run tests.

## Screenshots

`docs/design/screenshots/`: `home-desktop.png`, `home-phone.png`, `hero-listening.png`,
`character-states.png` (all 10 states, reduced motion), `command-execution-mode.png`,
`activity-drawer.png`, `analysis-collapsed-rail.png`.

## Known gaps / follow-ups

1. Everything a user sees is in European Portuguese since 0.3.7 (module screens, server
   messages, sign-in/account screens, onboarding and the native macOS shell); the older module
   layouts are not restyled beyond the theme.
2. The command workspace shows the execution flow: tasks by dependency stage
   (`GET /api/v1/plans/{id}/execution-graph`) and, per task, a step log of status changes,
   agent runs and tool attempts.
3. Notification titles are written in Portuguese by the server (0.3.5).
4. The public landing uses the Kiko Alive identity (logo, animated Kiko, midnight/amber) in
   Portuguese; sign-in, account and onboarding screens use the Kiko card and logo.
5. Packaged-app cold start and first paint should be instrumented in the QA program.
