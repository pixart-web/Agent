# GitHub integration

Phase 5A connects the Development Agent to GitHub without giving the LLM API access.

## Configuration and credentials

```env
GITHUB_INTEGRATION_ENABLED=false
GITHUB_TOKEN=
GITHUB_ALLOWED_REPOSITORIES=pixart-web/Agent
GITHUB_API_TIMEOUT_SECONDS=30
GITHUB_PROTECTED_BRANCHES=main
GITHUB_ALLOWED_BRANCH_PREFIXES=feature/,fix/,chore/,docs/
GITHUB_MAX_FILE_BYTES=500000
GITHUB_MAX_OUTPUT_CHARS=100000
```

A PAT is supported for local development. Production should use a GitHub App with
narrowly scoped installation tokens, short lifetimes, per-repository installation
permissions, and managed secret storage. The current token is resolved only inside the
worker through `CredentialProvider`.

`GET /api/v1/integrations/github/status` returns only enabled,
allowed_repositories, and credential_configured.

## Policy and safety

`RepositoryAccessPolicy` validates owner/name, operation, path, and branch before the
first external request. Repositories outside the environment allowlist are rejected.
Absolute paths, traversal, backslashes, known secret filenames, malformed refs, and
unsafe branch prefixes are rejected. Writes to protected branches such as `main` are
blocked.

File reads and writes are UTF-8 only and size bounded. Read output is truncated to the
configured output limit and tagged `external_content=true`, `trust=untrusted`.
Repository files, README text, issues, PR bodies, and comments are data, never system
instructions, and must not be concatenated into a system prompt.

## Tools

Read-only green tools:

- `github.get_repository`
- `github.list_branches`
- `github.read_file`
- `github.list_pull_requests`
- `github.get_pull_request`
- `github.list_issues`
- `github.get_issue`

Yellow tools requiring approval:

- `github.create_issue`
- `github.comment_issue`
- `github.create_branch`
- `github.create_or_update_file`
- `github.open_pull_request`

Only the Development Agent has these tools. GitHub proposals are automatically
dispatched into the Execution Engine: green reads queue normally, while yellow writes
stop at a fingerprinted approval. Each write remains a separate TaskAction.

File updates fetch the current blob SHA and include it in the GitHub request. A supplied
expected SHA must still match. Branch creation is predictable when the branch already
points at the requested source. Issue/comment idempotency keys use hidden markers, and
opening a PR reuses an evident existing open head/base pair.

## Client, errors, retries, and audit

`GitHubClient` isolates HTTP from handlers. Requests use a fixed GitHub API base URL,
a configured timeout, and typed errors for authentication, permission, not found, rate
limit, timeout, validation, and transient availability. Only timeout, 502/503/504, and
rate limits with a reasonable Retry-After are retryable. Write tools have no automatic
retry budget; their idempotency checks protect deliberate re-execution.

Safe rate-limit remaining/reset metadata may be returned. Raw API error bodies are never
exposed. Successful executions append GitHub-specific audit events containing only
repository, path/branch or issue/PR number, tool, execution ID, and correlation ID.

## Manual smoke test

The normal CI uses `FakeGitHubClient` and requires no token. An optional read-only test
is available:

```bash
python -m app.scripts.test_github_integration
```

Run it from `apps/api` with the integration enabled, a token, and an allowed
repository. It reads repository metadata and branches only. It never creates issues,
branches, files, comments, or pull requests.

Not implemented: merge, branch deletion, force push, secrets, Actions secrets, releases,
deployments, organization administration, repository deletion, or GitHub App
installation management.
