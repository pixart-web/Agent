# Kiko — Local test environment for the macOS app

A real, isolated and persistent Kiko backend on this Mac, so **Kiko for macOS** can be used
against `http://localhost:8000`. Everything is local: no Hetzner, no deployment, no
production credentials, no real customer data, no external email.

Verified on 2026-11-14 on `main` @ `e7da528` (Mac mini M4, macOS 27.2).

## 1. Why native services and not Docker Compose

`docker-compose.yml` is the generic development stack. It was not used here because:

- The Colima VM (the only Docker engine on this Mac) is stopped, is shared with other
  Pixart projects and is already near its disk limit, so no images are pulled into it.
- Its services publish the common ports `5432`/`6379` (a shared Homebrew PostgreSQL already
  listens on `5432`) and its volume names (`postgres_data`, `redis_data`) are not Kiko-specific.

Instead `scripts/local/kiko-local.sh` runs the same processes the Compose file runs, natively,
with Kiko-only ports, data directories and generated credentials. Nothing touches the shared
Homebrew PostgreSQL or any other project's database, Redis or volumes.

## 2. Services and addresses

| Service    | What runs                                                               | Address                                                  | Data                     |
| ---------- | ----------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------ |
| `postgres` | dedicated PostgreSQL **16** cluster (Homebrew `postgresql@16` binaries) | `127.0.0.1:55432`, db/user `kiko_local`                  | `~/.kiko-local/postgres` |
| `redis`    | dedicated Redis, password protected, AOF on                             | `127.0.0.1:56379` (db 0 app, db 1 Celery broker)         | `~/.kiko-local/redis`    |
| `mailpit`  | email capture, nothing is relayed                                       | SMTP `127.0.0.1:56025`, inbox **http://127.0.0.1:58025** | `~/.kiko-local/mailpit`  |
| `api`      | FastAPI (uvicorn), migrations applied on start                          | **http://localhost:8000**                                | —                        |
| `worker`   | Celery execution worker (`--pool=solo`)                                 | Redis db 1                                               | —                        |
| `outbox`   | outbox dispatcher (`app.scripts.run_outbox_dispatcher`)                 | —                                                        | —                        |
| `mailer`   | transactional email dispatcher → Mailpit                                | —                                                        | —                        |
| `web`      | Next.js web client (target of emailed links)                            | http://localhost:3000                                    | —                        |

All listeners are bound to `127.0.0.1`. State directory: `~/.kiko-local` (`chmod 700`)

- `secrets.env` — generated once (PostgreSQL password, Redis password, `AUTH_SECRET_KEY`), mode 600.
- `overrides.env` — your local overrides (AI key etc.), mode 600, read after the defaults.
- `run/` — pid files, generated `api.env` and `redis.conf`.
- `logs/` — one log per service.

The script never deletes `~/.kiko-local`; stopping or restarting keeps all data.

Prerequisites (already present on this Mac): Homebrew `postgresql@16`, `redis`, `mailpit`,
the repo venv `.venv` (Python 3.12, `pip install -e apps/api`), and `pnpm install` for the web
client.

## 3. Commands

```bash
scripts/local/kiko-local.sh start            # start everything (runs migrations + agent seed first)
scripts/local/kiko-local.sh status           # state of each service + /health + /ready
scripts/local/kiko-local.sh stop             # graceful stop, clients first, data stores last
scripts/local/kiko-local.sh restart          # stop + start, data kept
scripts/local/kiko-local.sh restart api worker outbox   # restart only some services
scripts/local/kiko-local.sh logs             # list log files
scripts/local/kiko-local.sh logs api -f      # follow one log (api, worker, outbox, mailer, web, postgres, redis, mailpit, migrate)
scripts/local/kiko-local.sh migrate          # alembic upgrade head + seed built-in agents
scripts/local/kiko-local.sh test             # backend smoke test (20 checks, fictitious data)
scripts/local/kiko-local.sh test-persisted   # after a restart: sign in again with the last test account
scripts/local/kiko-local.sh desktop-e2e      # real macOS app journey (debug build) against this backend
scripts/local/kiko-local.sh open-link URL    # open an emailed http://localhost:3000/... link in the app
scripts/local/kiko-local.sh psql             # psql on the kiko_local database
scripts/local/kiko-local.sh env              # print the non-secret configuration
```

Ports can be changed with `KIKO_LOCAL_PG_PORT`, `KIKO_LOCAL_REDIS_PORT`, `KIKO_LOCAL_SMTP_PORT`,
`KIKO_LOCAL_MAIL_UI_PORT`, `KIKO_LOCAL_API_PORT`, `KIKO_LOCAL_WEB_PORT`; the state directory with
`KIKO_LOCAL_HOME`. `start` refuses to run when a port is held by another process.

There is no command that removes data. To start from scratch, stop the services and move
`~/.kiko-local` aside yourself.

## 4. Connecting Kiko for macOS

1. `scripts/local/kiko-local.sh start`
2. Open Kiko → menu **Kiko → Server Connection…**
3. Enter `http://localhost:8000` and confirm the native dialog.

Plain `http` is accepted only for loopback hosts (`localhost`, `127.0.0.1`, `::1`); any other
server must use HTTPS. The choice is stored in
`~/Library/Application Support/pt.pixart.kiko/server.json` (already set to
`http://localhost:8000` on this Mac). The session (refresh token) is kept in the login Keychain
under service `pt.pixart.kiko.session`, account `http://localhost:8000`.

## 5. Email (registration, verification, password reset)

- `TRANSACTIONAL_EMAIL_ENABLED=true`, SMTP → Mailpit `127.0.0.1:56025`, no TLS, no auth,
  sender `kiko-local@example.com`. Mailpit accepts everything and delivers nothing outside.
- `AUTH_REQUIRE_EMAIL_VERIFICATION=true` — verification stays **on**; an unverified account
  gets `403 Email verification required` at login.
- Read the emails at **http://127.0.0.1:58025**.
- Links in the emails point to the web client (`PUBLIC_WEB_URL=http://localhost:3000`), which
  the script runs, so clicking them in Mailpit works in the browser. To complete them **in the
  macOS app** instead, copy the link and run
  `scripts/local/kiko-local.sh open-link 'http://localhost:3000/verify-email?token=…'`
  (it opens `kiko://verify-email?token=…`; also works for reset-password and invite links).
  Works whether Kiko is already open or not (cold-start links were fixed, see section 9).
- Use fictitious addresses only (`…@example.com`).

## 6. AI provider

The backend supports two providers (`apps/api/app/core/config.py`, `docs/ai-providers.md`):

- `openai` — the real provider (Responses API, structured outputs), needs `OPENAI_API_KEY`.
- `fake` — deterministic, injected by automated tests only; it is **not** usable at runtime
  (the factory raises "Fake AI provider must be injected by the application").

The local environment runs `AI_PROVIDER=openai` **without a key**. The result:

- Supervisor “Gerar plano com Supervisor” → HTTP 503 `OpenAI is not configured`, shown in the UI.
- Kiko AI conversations are created, but no assistant answer is generated.
- Manual plans, tasks, human plan approval, governed actions, the Approvals centre and the
  Celery execution of approved actions all work without AI.

To enable real AI (an OpenAI paid service; use only a key you are authorised to use), add to
`~/.kiko-local/overrides.env`:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.4-mini
```

then `scripts/local/kiko-local.sh restart api worker outbox`. Optional check:
`(set -a; . ~/.kiko-local/run/api.env; set +a; cd apps/api && ../../.venv/bin/python -m app.scripts.test_supervisor_provider)`.
No key was configured or used while preparing this environment.

## 7. Test procedure and results (2026-11-14)

### 7.1 Backend smoke test — `kiko-local.sh test` (20/20 PASS, run 4×)

Real HTTP against `http://127.0.0.1:8000` with a fresh fictitious account each run:

```
PASS API health / API readiness (database + redis)
PASS register fictitious user · login refused before email verification (403)
PASS verification email captured by Mailpit · verify email with emailed token
PASS login after verification · authenticated /auth/me
PASS session refresh rotates the refresh token
PASS workspace exists for new account · onboarding completes workspace setup
PASS password reset email captured by Mailpit · password reset confirm
PASS old password rejected after reset (401) · login with new password
PASS logout · refresh refused after logout (replays the logged-out token → 401)
PASS PostgreSQL persisted user and workspace membership (queried with psql)
PASS Redis read/write
PASS Celery worker online with execution tasks registered
```

### 7.2 Restart and recovery — `restart` + `test-persisted` (5/5 PASS)

All eight services stopped (PostgreSQL fast shutdown, Redis `SHUTDOWN` with save) and started
again; migrations re-checked (`20261014_0035 (head)`); the account created before the restart
signed in, its completed workspace was intact, Redis and the Celery worker answered.

### 7.3 Kiko for macOS 0.1.0 (installed release build) ↔ local API

- Launched `/Applications/Kiko.app` with `server.json` = `http://localhost:8000`: the API log
  shows its `GET /api/v1/auth/me` → 401 and `POST /api/v1/auth/refresh` → 401 (no session yet,
  so the app shows sign-in). This proves the installed app reaches the local API.
- `open-link` with a real emailed verification link while the app was open: macOS handed
  `kiko://verify-email?token=…` to the installed app, the app called
  `POST /api/v1/auth/verify-email` → 200, and the account became verified in PostgreSQL.

### 7.4 Real-app journey — `kiko-local.sh desktop-e2e`

The debug build of the same app drives its real WKWebView through the UI (see
`KIKO-MACOS-TESTING.md`), against this backend at `http://127.0.0.1:8000` (a different Keychain
account than your own `localhost` session). The full journey (26 UI steps + 2 Keychain
checks) **passed 5 out of 5 times** after the two app fixes in section 9:

```
register · open registration · submit registration · unverified account cannot sign in
verify email with emailed token · sign in · configure company (workspace onboarding)
refresh token stored in Keychain · session restored from Keychain after relaunch
submit a command · Supervisor without an AI provider shows an honest unavailable state
create a manual plan · add a task · approve the plan · mark the task ready
dispatch a governed action that requires approval · approve it in the Approvals centre
approved action executed by the backend worker (Celery) · task persisted and opens
create a project · Kiko AI conversation · create a CRM contact
relaunch restores session and last screen · CRM contact persisted · project persisted
log out (Keychain item removed) · relaunch after logout requires sign-in
```

Before the notification fix, only 3 of 10 runs passed (after the two set-up issues in
section 8 were solved: the Celery pool and the test's AI-unavailable message). 6 failures
were the app freeze described in section 9 (fixed issue A): a screen stayed on "Loading…"
even though the API had answered every request with 200. The seventh failure was the auth
rate limit (limitation 1), hit by running many journeys back to back. After the fix, 5 runs
spaced 60 s apart all passed.

## 8. Troubleshooting

| Symptom                                                                                     | Cause / fix                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pg_ctl: could not start server`, log says _postmaster became multithreaded during startup_ | macOS locale issue; the script starts PostgreSQL with `LC_ALL=C`. If you start it by hand, do the same.                                                                                                                       |
| `port … is used by another process`                                                         | Another program holds the port. Find it with `lsof -nP -iTCP:<port> -sTCP:LISTEN`, or choose another port with the `KIKO_LOCAL_*_PORT` variables.                                                                             |
| Worker log: `ValueError: not enough values to unpack (expected 3, got 0)`                   | Celery's prefork pool on macOS (spawn start method). The script uses `--pool=solo`; do not start the worker with the default pool. An execution dispatched while that happened stays `queued` until stale-execution recovery. |
| `429 Too Many Requests` on login/refresh, app falls back to sign-in                         | Auth rate limit (10 requests per minute per IP and action). Wait a minute. It is kept enabled on purpose.                                                                                                                     |
| No email in Mailpit                                                                         | `logs mailer` (dispatcher) and `logs mailpit`. The dispatcher retries with back-off.                                                                                                                                          |
| App shows “can’t reach the server”                                                          | `status`; the API must answer `http://localhost:8000/health`. Check **Kiko → Server Connection…** shows `http://localhost:8000`.                                                                                              |
| `migration failed`                                                                          | `logs migrate`.                                                                                                                                                                                                               |
| Kiko AI / Supervisor say AI unavailable                                                     | Expected without `OPENAI_API_KEY` (section 6).                                                                                                                                                                                |

## 9. App defects found and fixed while preparing this environment

**A. Intermittent freeze after a native notification.** `notify`
(`apps/desktop/src-tauri/src/commands.rs`) was an `async` command that called the blocking
`notify_rust` / `mac-notification-sys` `show()`. A process sample taken during a freeze showed
a tokio worker thread parked in `send_mac_notification → rust_wait_for_delivery`; IPC
requests queued on that worker never ran, so a screen stayed on "Loading…" after a new
notification arrived (for example after an approval). The notification now runs on the
blocking pool (`tauri::async_runtime::spawn_blocking`) and the command returns at once.

**B. Deep link ignored on cold start.** When `kiko://…` launched the app, `lib.rs` emitted
the navigate event during `setup`, before the WebView listened, so the link was lost. The shell
now keeps that route (`deep_link::PendingRoute`), and the UI collects it through the new
`take_pending_route` command right after it registers its navigation listener
(`components/desktop-shell.tsx`). Later links are delivered as live events, as before.

Tests: Rust 21 (new `pending_route_is_kept_until_the_ui_listens`), Vitest 64 (new bridge
test). The fixes are on this branch; the Kiko 0.1.0 DMG installed earlier does **not** have
them. Install the DMG rebuilt from this branch to get them.

## 10. Known limitations

1. **Auth rate limit applies locally.** Many sign-ins/relaunches within a minute from the same
   IP get `429` (seen when running the desktop journey repeatedly). Wait a minute.
2. **No real AI**: without an OpenAI key the Supervisor and Kiko AI answers are unavailable
   (section 6).
3. **Email, calendar, GitHub and Codex integrations are disabled** (they need real Google/GitHub
   OAuth credentials, which must not be used here).
4. **Celery runs `--pool=solo`**: one task at a time, and Celery soft time limits do not
   interrupt a running task (prefork-only feature). Production (Linux containers) is unaffected.
5. **Emailed links point to the web client**, not to `kiko://`. Use `open-link` to finish them
   in the app.
6. Native UI interaction in the release app (clicking through Server Connection by hand) was
   not automated; the setting was already stored by the app, and the app's own requests prove
   it is used.

## 11. Data hygiene

- Every account created by the tests is fictitious (`local-smoke-*`, `desktop-e2e-*`,
  `local-deeplink-*` @example.com) and lives only in `~/.kiko-local`.
- `desktop-e2e` removes its Keychain item (`http://127.0.0.1:8000`) at start and end; it never
  touches your `http://localhost:8000` session.
- Secrets in `~/.kiko-local/secrets.env` were generated for this Mac and are not used anywhere
  else. Do not commit them.
