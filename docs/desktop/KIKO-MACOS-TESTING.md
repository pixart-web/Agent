# Kiko for macOS — testing

All results below were produced on 2026-11-14 on an Apple Silicon Mac (macOS 27.2) unless
marked otherwise. Nothing here was run against staging or production.

## 1. Automated suites

| Suite                             | Command                                                          | Result                     |
| --------------------------------- | ---------------------------------------------------------------- | -------------------------- |
| Rust unit tests (desktop)         | `cargo test` in `apps/desktop/src-tauri`                         | **20 passed**              |
| Rust lint/format                  | `cargo clippy --all-targets -- -D warnings`, `cargo fmt --check` | clean                      |
| Web unit tests (incl. desktop)    | `pnpm test`                                                      | **63 passed** (50 → 63)    |
| Web typecheck / ESLint / Prettier | `pnpm typecheck`, `pnpm lint`, `pnpm format:check`               | clean                      |
| Web production build (unchanged)  | `pnpm build`                                                     | 38 pages built             |
| Desktop static export             | `pnpm --filter @agent/desktop run build:ui`                      | exported with placeholders |
| Backend                           | `pytest apps/api`                                                | 251 passed, 6 skipped      |

Rust tests cover: path/method/header allowlists, traversal and redirect-free proxying rules,
refresh-cookie parsing, token stripping, retry safety, server URL validation, deep-link
parsing (incl. traversal and oversized tokens), external-link allowlist, file-name
sanitisation, protocol placeholder rewriting and menu routes.

Vitest covers: placeholder route params, desktop export gating, IPC request serialisation
(JSON and multipart), 204 handling, offline errors and connectivity events, restorable routes,
command-palette filtering, external-link detection and FastAPI error formatting.

## 2. Real desktop E2E (`apps/desktop/e2e`)

Browser-only tests do not prove the bundle works, so the journey runs **inside the real
WKWebView of the Kiko app**. A debug-only harness (`src-tauri/src/smoke.rs`, compiled out of
release builds) injects a script that drives the actual UI through the DOM; every API call
goes through the production IPC bridge and Keychain code to a real local backend
(PostgreSQL, Redis, Celery worker, outbox dispatcher).

The simplest way to get that backend is the local test environment
([KIKO-LOCAL-TEST-ENVIRONMENT.md](KIKO-LOCAL-TEST-ENVIRONMENT.md)):
`scripts/local/kiko-local.sh start` then `scripts/local/kiko-local.sh desktop-e2e`.

```bash
# API, outbox dispatcher and Celery worker running locally with an isolated database
KIKO_API_URL=http://127.0.0.1:8765 API_PYTHON=.venv/bin/python PYTHONPATH=apps/api \
  apps/desktop/e2e/run-journey.sh
```

Latest result (three consecutive runs, all green):

```
[register] launch without a session opens sign-in · open registration · submit registration ·
           unverified account cannot sign in
[verify]   verify email with emailed token · sign in · configure company
[keychain] refresh token stored after sign-in
[work]     session restored from Keychain after relaunch · submit a command ·
           Supervisor without an AI provider shows an honest unavailable state ·
           create a manual plan · add a task · approve the plan (human plan approval) ·
           mark the task ready · dispatch a governed action that requires approval ·
           approve it in the Approvals centre · approved action executed by the backend worker ·
           task persisted and opens from the task list · create a project ·
           Kiko AI conversation · create a CRM contact
[persist]  relaunch restores session and last screen · CRM contact persisted ·
           project persisted · log out
[keychain] session item removed by logout
[after-logout] relaunch after logout requires sign-in
ALL PHASES PASSED — 27 steps, 5 app launches
```

Each phase is a separate process launch, so "quit and reopen" is exercised for real.

## 3. Release bundle validation (manual run, recorded)

| Check                                                 | Result                                                       |
| ----------------------------------------------------- | ------------------------------------------------------------ |
| DMG mounts, contains `Kiko.app` + `Applications` link | yes                                                          |
| `codesign --verify --deep --strict`                   | passes (ad-hoc signature, hardened runtime)                  |
| Gatekeeper (`spctl -a`)                               | **rejected** — expected: not Developer ID signed / notarized |
| Bundle id / version / min macOS                       | `pt.pixart.kiko` / 0.1.0 / 12.0                              |
| URL scheme declared                                   | `kiko`                                                       |
| Entitlements                                          | `com.apple.security.network.client` only                     |
| Architecture                                          | arm64                                                        |
| Installed size / DMG size                             | 7.4 MB / 5.0 MB                                              |
| Release app talks to local API                        | yes                                                          |

## 4. Performance (release build, this Mac)

| Metric                                | Measured                   | Budget   |
| ------------------------------------- | -------------------------- | -------- |
| Launch → first authenticated API call | 0.57 s first, 0.3 s repeat | < 1.5 s  |
| App process RSS after 8 s             | 94–99 MB                   | < 200 MB |
| WebKit content processes RSS          | 83–94 MB                   | < 250 MB |
| CPU when idle                         | 0.0 %                      | < 1 %    |
| DMG size                              | 5.0 MB                     | < 30 MB  |

The "first" launch was not a true cold boot (files were cached from the build). Measure
again on a clean machine before a public release.

## 5. Not yet verified (honest gaps)

- **OS-level deep links**: route parsing is unit-tested, but `open kiko://…` could not be
  exercised because LaunchServices does not bind schemes for apps in temporary folders and
  the app was not installed into `/Applications` without owner consent.
- **Real AI provider**: Supervisor planning and Kiko AI answers need `AI_PROVIDER=openai`
  and a key; the app's unavailable state was verified instead.
- **Native dialogs, notifications banners, menu clicks and the save panel** need a person
  (or UI automation with Accessibility permission) to click them.
- **Gmail/Calendar OAuth hand-off, GitHub/Codex**: providers disabled in the test backend.
- **Workspace switching, invitations, password reset, Marketing, Automations, Knowledge
  upload, Calendar, Email** reuse the web code paths but have no desktop E2E step yet.
- **Accessibility** (VoiceOver, keyboard-only, contrast) on the desktop shell.
- **Intel Macs**.

## 6. Owner test checklist

1. Install from the DMG (right-click → Open the first time; see release readiness).
2. Kiko → Server Connection… → enter the test server, confirm the native dialog.
3. Register, open the verification link, sign in, complete onboarding.
4. ⌘K palette, ⌘1–8 navigation, ⌘[ / ⌘] history, ⌘R reload.
5. Create a command, manual plan and task; approve the plan; dispatch
   `internal.simulate_external_action`; approve it in Approvals; see it complete.
6. With an AI provider on the server: generate a Supervisor plan, use Kiko AI.
7. CRM: create a contact, export CSV (native save panel).
8. Disconnect a Calendar/Email account (native confirmation).
9. Turn Wi-Fi off: the offline banner appears; nothing is reported as saved.
10. Quit (⌘Q) and reopen: same screen, still signed in. Log out, reopen: sign-in screen.
11. Keychain Access → search `pt.pixart.kiko.session`: present while signed in, gone after
    logout.
