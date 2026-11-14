# Kiko for macOS — roadmap and status

Durable handoff document. Update the status column whenever a phase changes.

| Phase | Goal                                 | Status (2026-11-14)                                                                                                                                                                                                                                                 |
| ----- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M0    | State recovery and baseline audit    | **Done** — `docs/audits/KIKO-DESKTOP-TRANSITION-BASELINE.md`                                                                                                                                                                                                        |
| M1    | Commercial integration stabilization | **Waiting for the owner** — PR #31 is green and mergeable; the merge was blocked by the agent permission policy and must be done by the owner. Manifest aligned to `d6a6808`.                                                                                       |
| M2    | Desktop foundation                   | **Done** — Tauri 2 app, static export, `kikoui://` protocol, Rust API proxy, CI job                                                                                                                                                                                 |
| M3    | Authentication and workspaces        | **Done (core)** — login/refresh/logout via Keychain, registration, verification, onboarding, server connection. Workspace switching reused from web, no desktop E2E yet.                                                                                            |
| M4    | Kiko AI and operations               | **Done (UI wired)** — conversations, commands, manual plans, tasks, plan approval, governed actions, approvals, execution verified E2E. AI planning needs a provider-enabled backend.                                                                               |
| M5    | Business modules                     | **Partial** — CRM verified E2E; Marketing, Automations, Knowledge, Calendar, Email, Integrations run the shared web code but are not desktop-E2E-tested. OAuth hand-off moved to the system browser.                                                                |
| M6    | Native macOS experience              | **Done (core)** — menus, shortcuts, palette (⌘K), sidebar, window state, last screen, notifications (polling), save panel, native confirmations, deep links, offline banner. Menu-bar companion **deferred** (not needed for owner testing; would duplicate state). |
| M7    | Pixart ecosystem foundation          | **Design done** — `KIKO-PIXART-ECOSYSTEM.md`; no live connectors (no verified product APIs).                                                                                                                                                                        |
| M8    | Security, QA and performance         | **Done for this RC** — IPC/capability review, 2 defects fixed, 20 Rust + 63 web tests, desktop E2E ×3 green, performance measured. Gaps listed in testing doc.                                                                                                      |
| M9    | macOS test release                   | **Development build produced** — ad-hoc signed `.app` + `.dmg`; Developer ID signing and notarization blocked on Apple credentials.                                                                                                                                 |

## Defects found and fixed during this roadmap

| Severity | Defect                                                                                 | Fix                                     |
| -------- | -------------------------------------------------------------------------------------- | --------------------------------------- |
| HIGH     | Destructive confirmations did not block in the desktop app (`window.confirm` is async) | native `confirm_action` + ESLint guard  |
| HIGH     | A compromised WebView could silently switch the API server (credential phishing)       | native confirmation in `set_server_url` |
| MEDIUM   | Intermittent hang when reusing a keep-alive connection the server had closed           | 4 s pool idle timeout + safe GET retry  |
| MEDIUM   | Validation errors rendered as `[object Object]` (web and desktop)                      | `describeErrorDetail`                   |
| LOW      | Offline Alembic SQL generation failed for migration 0034 (CI)                          | explicit SQL inserts                    |

## Next steps (in order)

1. Owner merges PR #31, then this branch is rebased onto `main` by merge (no force-push).
2. Provide an authorized HTTPS staging backend reachable from the Mac and set it as
   `KIKO_DEFAULT_API_URL` for internal builds.
3. Enable an AI provider on staging; extend the E2E with Supervisor planning and Kiko AI.
4. Apple Developer ID + notarization in CI (secrets in GitHub, never in the repo).
5. Tauri updater with a signing key and a private feed; release channels.
6. Desktop E2E steps for Marketing, Automations, Knowledge upload, workspace switching,
   invitations, password reset.
7. Universal (Intel + Apple Silicon) build once Intel test hardware is available.
8. Windows (P2) on the same crate.
