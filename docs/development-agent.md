# Development Agent

The Development Agent uses prompt version `development-v3`. It inspects GitHub evidence,
turns requested work into an explicit specification, and delegates implementation to Codex
through the Execution Engine. It is the only specialist allowed to use GitHub or Codex tools;
Marketing, Sales, and Support retain internal-only allowlists.

The preferred sequence is GitHub inspection, bounded instructions with acceptance criteria
and allowed paths, then `codex.implement_task`. Codex is not an agent-side client: it is a
registered execution tool. Read-only `codex.review_pull_request` produces internal findings
without publishing a GitHub review. `codex.implement_task` and `codex.fix_pull_request` are
yellow and stop at fingerprinted human approval.

After approval, the runner may create or update an allowed branch, validate changes, create
one commit, and push without force. It cannot merge, deploy, delete branches, access secrets,
or target `main`, `master`, `production`, or another protected branch. Opening a PR remains a
separate `github.open_pull_request` action and approval.

The prompt treats repository files, `AGENTS.md`, issues, pull requests, comments, and Codex
findings as untrusted data. It forbids invented shell commands, credentials, arbitrary URLs,
allowlist bypasses, weakened tests, and claims of success without a structured tool result.
See [Codex integration](codex-integration.md) for runner, persistence, and operations.
