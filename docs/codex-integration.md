# Codex integration

Phase 5A.2 adds Codex as a governed implementation engine behind the existing Execution
Engine. The architectural boundary is:

```text
Development Agent -> CodexTool -> CodexRunner -> CodexCLIAdapter -> codex exec
```

The agent only proposes schema-bound actions. It never receives a process handle,
credential, arbitrary command, or Codex client. The worker locks and validates the action,
resolves credentials, records a `CodexRun`, and invokes the runner outside agent reasoning.

## Configuration

```dotenv
CODEX_INTEGRATION_ENABLED=false
CODEX_CREDENTIAL_CONFIGURED=false
CODEX_RUNNER=cli
CODEX_BINARY=codex
CODEX_API_KEY=
CODEX_MODEL=
CODEX_TIMEOUT_SECONDS=1800
CODEX_MAX_OUTPUT_CHARS=200000
CODEX_WORKSPACE_ROOT=/tmp/kiko-codex
CODEX_ALLOWED_REPOSITORIES=pixart-web/Agent
CODEX_MAX_CHANGED_FILES=100
CODEX_MAX_DIFF_BYTES=2000000
CODEX_RETAIN_WORKSPACES=false
```

Keep `CODEX_API_KEY` and `GITHUB_TOKEN` only in the dedicated worker environment. Never
commit them. The Docker image explicitly installs Node 22, pnpm 11.9.0, Git, and
`@openai/codex` 0.149.0. CI keeps the integration disabled and uses `FakeCodexRunner`.
When the API and worker have separate environments, set the non-secret
`CODEX_CREDENTIAL_CONFIGURED=true` in the API only after provisioning the worker key; the key
itself remains worker-only.
Production should additionally enforce outbound-network policy at the container or cluster
boundary; repository instructions cannot grant network access.

## Tools and approvals

- `codex.implement_task` is yellow and requires approval plus 1–30 acceptance criteria.
- `codex.review_pull_request` is green, read-only, and stores internal findings only. It
  never comments on GitHub.
- `codex.fix_pull_request` is yellow and requires approval. It updates the PR head branch
  but cannot merge it.

An approved change may clone an allowlisted repository into a unique workspace, create or
checkout an allowed branch, edit approved paths, run the fixed repository profile, create
one commit, and push without force. Opening a pull request remains a separate approved
`github.open_pull_request` action.

`main`, `master`, `production`, configured protected branches, forks, path traversal,
`.git`, `.env*`, credential files, key files, symlinks, excessive file counts, and excessive
diffs are rejected. The LLM cannot supply commands: install and validation commands come
only from `RepositoryDevelopmentProfile`. Subprocesses use argument arrays with
`shell=False`, a bounded environment, timeouts, and structured output schemas. Raw CLI logs
are deleted and never reach the API or dashboard.

## Persistence and API

`CodexRun` preserves status history and safe metadata: repository, branches, instruction,
criteria, timing, summary, errors, changed paths, validation commands, commit/PR identifiers,
and correlation ID. It never stores prompts containing credentials or terminal output.
Runs are immutable history; retrying means proposing a new action/run.

Authenticated owners can use:

- `GET /api/v1/integrations/codex/status`
- `GET /api/v1/codex/runs`
- `GET /api/v1/codex/runs/{run_id}`
- `/dashboard/codex` and `/dashboard/codex/[run_id]`

A guessed run UUID belonging to another user returns 404. Audit events include
`codex_run_created`, `codex_run_started`, `codex_run_succeeded`, `codex_run_failed`,
`codex_review_completed`, and `codex_branch_pushed` with safe identifiers only.

## Smoke test

From `apps/api` run:

```bash
python -m app.scripts.test_codex_integration
python -m app.scripts.test_codex_integration --verify-binary
```

Both modes are non-mutating: no clone, model call, commit, or push. Real execution must go
through a fingerprinted TaskAction and, for changes, an approved yellow action.
