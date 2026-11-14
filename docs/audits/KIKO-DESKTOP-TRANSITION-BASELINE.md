# Kiko desktop transition baseline (M0)

**Audit date:** 2026-11-14  
**Auditor:** Claude Code (taking over from Codex)  
**Scope:** repository state, architecture, defects and constraints relevant to a macOS-first desktop
client. No staging or production system was touched.

## 1. Verified Git state

| Item                       | Value                                                                    |
| -------------------------- | ------------------------------------------------------------------------ |
| Remote                     | `https://github.com/pixart-web/Agent.git`                                |
| `origin/main`              | `80f12260e97d3b696f5cb22df07283d1444f2312`                               |
| `codex/commercial-release` | `d6a6808` → `36e92df` (manifest/readiness alignment added in this audit) |
| PR                         | pixart-web/Agent#31, open, `MERGEABLE`, merge state `CLEAN`              |
| CI on `d6a6808`            | run `43590618786`: Frontend, Backend, Container build, PG/Redis — pass   |
| Branch protection (`main`) | none configured; operator has admin permission                           |
| Local working tree         | clean before this audit; no stashes                                      |
| Other branches             | 3 historical `feature/*` (already in `main`), 13 Dependabot branches     |
| Migration head             | `20261014_0035` (single linear head)                                     |

No commits from other authors or agents appeared after `d6a6808`. The only workflow is `ci.yml`
(push/PR CI); **nothing deploys on push to `main`**, so merging PR #31 has no production effect.

### Manifest consistency

`deploy/release-manifest.json` named `000466e` as the source revision, but two later commits
(`41dee30` docs, `d6a6808` migration 0034 offline-SQL fix) were on the branch. The manifest now names
`d6a6808`, keeps a revision history, and marks the local image IDs as superseded evidence that must be
rebuilt before staging. The readiness document carries a dated addendum.

## 2. Architecture

```
apps/api   FastAPI (Python 3.12) · SQLAlchemy 2 · Alembic · PostgreSQL · Redis/Celery workers
apps/web   Next.js 15 App Router · React 19 · 45 client components · ~10.8k lines TS/TSX
packages/shared   @agent/shared — domain constants and types used by the web app
deploy/    compose.production.yml + release manifest (no automated deploy)
```

- **API surface:** 26 routers under `/api/v1` (auth, workspaces, conversations, commands, plans,
  supervisor, execution, tasks, projects, agents, specialized agents, approvals via execution,
  CRM/client management, marketing, automations, knowledge, email, calendar, codex, integrations,
  notifications, operations, commercial, data portability, platform admin) plus health/metrics.
- **Execution model:** Supervisor produces versioned structured plans; Execution Engine runs governed
  steps with risk classification, approval fingerprints, idempotency keys, allowlists, outbox and
  audit. External writes only happen through this path.
- **Progress delivery:** no SSE/WebSocket endpoints exist. Clients poll authenticated endpoints.
- **Tenancy:** every business aggregate is workspace-scoped; membership and role are resolved
  server-side; foreign IDs return 404.

## 3. Functional modules (repository state)

Complete and tested per the commercial readiness document: identity lifecycle, workspaces/RBAC,
onboarding, Kiko conversations, commands/plans/tasks/projects, agent center, approvals, CRM,
marketing, automations, knowledge ingestion, notifications, analytics, team/settings, commercial
plans/entitlements, portability/retention, synthetic demo.

Provider-backed paths (Gmail, Calendar, SMTP, GitHub, Codex, OpenAI, billing) are implemented as
fail-closed adapters and **have never been exercised with real credentials**.

## 4. Incomplete features and known defects

| Severity | Item                                                                                  |
| -------- | ------------------------------------------------------------------------------------- |
| —        | No BLOCKER/HIGH code defect known (commercial security review, re-checked here)       |
| MEDIUM   | No MFA (documented limitation)                                                        |
| LOW      | Style CSP keeps `'unsafe-inline'`                                                     |
| LOW      | Starlette `TestClient` deprecation warning in tests                                   |
| GATE     | Real-provider journeys, staging, registry digests, legal/pricing — outside repository |
| FIXED    | Offline Alembic SQL for migration 0034 failed CI (`d6a6808`)                          |

## 5. Desktop compatibility findings

1. **Routing.** The web app relies on Next.js App Router with 15 dynamic segments (`[id]`, etc.) read
   through `useParams`. A static export (needed to bundle UI in the app) requires
   `generateStaticParams`, which client components cannot export. Dynamic routes need a desktop
   strategy (placeholder segment + client-side param resolution, or a desktop router).
2. **Authentication transport.** Access tokens live in JS memory; the refresh token is an
   `HttpOnly` cookie scoped to `/api/v1/auth`. A WebView on a custom scheme (`tauri://localhost`)
   is cross-origin to the API, so cookies would be third-party and `SameSite`-restricted. Copying
   the browser model into a WebView is not viable.
3. **CORS / Origin checks.** `WEB_ORIGINS` must be HTTPS in production and `require_allowed_origin`
   rejects unknown `Origin` headers on auth routes. A WebView origin such as `tauri://localhost`
   would need a backend allowlist change. Requests issued by native (Rust) code carry no `Origin`
   header and are accepted without backend changes.
4. **Production API URL.** `resolveApiBaseUrl` returns `''` (same origin) in production. The desktop
   build needs an explicit, allowlisted backend origin.
5. **Links in emails.** Verification/reset emails link to the web origin. Desktop needs either a
   deep-link scheme or a token-entry fallback.
6. **No push channel.** Notifications must be obtained by polling until a push channel exists.

## 6. Authentication implications

Recommended v1 model (no backend change required):

- The Rust core is the only component that talks to the auth endpoints. It posts credentials to
  `/api/v1/auth/login`, extracts `agent_refresh_token` from `Set-Cookie`, stores it in the macOS
  Keychain, and keeps the access token in Rust memory.
- All API traffic from the UI goes through a validated IPC command (`api_request`) that only accepts
  relative `/api/v1/...` paths and attaches the bearer token in Rust. **Neither token is ever
  exposed to JavaScript**, so XSS in the WebView cannot exfiltrate credentials.
- Refresh rotation and reuse detection continue to be enforced by the backend unchanged.
- Kiko is its own identity provider with password login. Browser-based OAuth 2.0 + PKCE would
  require Kiko to become an authorization server; that is documented as the future SSO path for the
  Pixart ecosystem, not a v1 requirement.

Optional future API change (documented, not required): a dedicated `/api/v1/auth/native/*` family
that returns the refresh token in the body with a `client_type=desktop` session label, so sessions
can be listed and revoked per device.

## 7. Security risks to manage in the desktop client

- WebView compromise must not yield tokens → tokens stay in Rust (above).
- IPC must be minimal and validated: path allowlist, method allowlist, size limits, no shell, no
  arbitrary filesystem.
- Remote content must never get IPC: the window loads only bundled assets; external links open in
  the system browser after scheme validation.
- Deep links must be parsed strictly and never trigger writes without user interaction.
- No production secrets in the bundle; backend URL is configuration, not a secret.
- Updates must be signature-verified (Tauri updater with minisign key) and disabled until a key and
  trusted feed exist.

## 8. Proposed implementation architecture

```
apps/desktop/                 Tauri 2 shell (Rust)
  src-tauri/                  auth, keychain, api proxy, menus, deep links, notifications, window state
  scripts/                    desktop build of the existing web UI (static export)
apps/web/                     unchanged web product + platform adapter (web | desktop)
packages/shared/              existing domain types (reused by both)
```

The desktop UI is the **existing Next.js product compiled as a static export** with a
`desktop` platform adapter for API transport, auth and navigation. This preserves every module
without rebuilding them and keeps one UI code base for Web and macOS (and later Windows). Native
capabilities live in Rust and are reached through a small, typed bridge.

## 9. Test baseline (measured 2026-11-14, local macOS arm64)

| Suite                         | Result                                             |
| ----------------------------- | -------------------------------------------------- |
| Backend pytest                | 251 passed, 6 skipped (PG/Redis tests run in CI)   |
| Offline Alembic (CI commands) | pass                                               |
| PostgreSQL upgrade/downgrade  | 0033 → head → 0033 pass on local PostgreSQL        |
| Ruff check/format             | pass                                               |
| Web Vitest                    | 50 passed (18 files)                               |
| Web typecheck / ESLint        | pass                                               |
| Prettier                      | pass                                               |
| Playwright E2E                | not re-run in this audit (6/6 reported at 000466e) |

## 10. Toolchain on the build Mac

- macOS 27.2, Apple Silicon (arm64), Node 26, pnpm 11.9.
- Xcode **not installed** — only Command Line Tools. Tauri macOS bundling (`.app`, `.dmg`) works
  with CLT (`clang`, `codesign`, `hdiutil`).
- **No code-signing identity** in the keychain → only unsigned/ad-hoc development builds are
  possible here. Developer ID signing and notarization are blocked on Apple credentials.

## 11. Recommended execution sequence

1. M1 — merge PR #31 (CI green, no deploy trigger), branch `feat/kiko-macos-desktop` from `main`.
2. M2 — Tauri 2 shell, static-export pipeline, Rust API proxy, CI job for desktop.
3. M3 — native login/refresh/logout with Keychain; registration/verification/reset via the same UI.
4. M4–M5 — wire existing modules through the bridge; verify each against a real local backend.
5. M6 — menus, shortcuts, window state, notifications (polling), deep links, offline state.
6. M7 — ecosystem documents (registry, contracts, SSO plan) without fictional connectors.
7. M8–M9 — security review of IPC/capabilities, desktop smoke tests, `.app`/`.dmg`, readiness report.
