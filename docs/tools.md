# Tool registry

`ToolRegistry` is the sole route from an approved action to executable code. The LLM
never calls handlers directly.

Every `ToolDefinition` declares name, version, description, allowed agent types, minimum
risk, timeout, retry budget, approval requirement, Pydantic input/output schemas, and a
handler. Unknown tools, unsupported versions, invalid schemas, and unauthorized agent
assignments are rejected before queueing.

Built-in Phase 3C tools:

| Tool                                | Risk   | Approval | Effect                                                         |
| ----------------------------------- | ------ | -------- | -------------------------------------------------------------- |
| `internal.echo`                     | green  | no       | Returns text                                                   |
| `internal.summarize`                | green  | no       | Uses the provider-neutral AI layer                             |
| `internal.create_note`              | green  | no       | Stores note content as the execution result linked to the Task |
| `internal.simulate_external_action` | yellow | yes      | Returns a simulated success only                               |
| `internal.simulate_critical_action` | red    | yes      | Returns a simulated success only                               |

Phase 5A GitHub tools are available only to the Development Agent:

| Tools                                                               | Risk   | Approval |
| ------------------------------------------------------------------- | ------ | -------- |
| `github.get_repository`, `github.list_branches`, `github.read_file` | green  | no       |
| `github.list_pull_requests`, `github.get_pull_request`              | green  | no       |
| `github.list_issues`, `github.get_issue`                            | green  | no       |
| `github.create_issue`, `github.comment_issue`                       | yellow | yes      |
| `github.create_branch`, `github.create_or_update_file`              | yellow | yes      |
| `github.open_pull_request`                                          | yellow | yes      |

GitHub handlers receive credentials only through the worker's internal ExecutionContext.
Their schemas never accept tokens or URLs. Repository, path, branch, protected-branch,
size, UTF-8, timeout, output, and retry policies are enforced before or around the client
call. See [GitHub integration](github-integration.md) for boundaries and exclusions.

Phase 5A.2 Codex tools are available only to Development:

| Tool                        | Risk   | Approval | Effect                                                                |
| --------------------------- | ------ | -------- | --------------------------------------------------------------------- |
| `codex.implement_task`      | yellow | yes      | Isolated implementation, fixed validation, one commit and branch push |
| `codex.review_pull_request` | green  | no       | Internal read-only analysis; no GitHub comment                        |
| `codex.fix_pull_request`    | yellow | yes      | Approved fixes on the existing PR branch; no merge                    |

Codex schemas accept specifications, not commands or credentials. Automatic retries are zero;
a new attempt is a new auditable action and `CodexRun`. PR creation remains a separate
`github.open_pull_request` action. See [Codex integration](codex-integration.md).

Phase 5B email tools use version 2:

| Tools                                                                  | Agents         | Risk   | Approval |
| ---------------------------------------------------------------------- | -------------- | ------ | -------- |
| email.list_messages, email.get_message, email.get_thread, email.search | Support, Sales | green  | no       |
| email.send                                                             | Sales          | yellow | yes      |
| email.reply                                                            | Support, Sales | yellow | yes      |
| email.mark_read                                                        | Support        | yellow | yes      |

Tokens are resolved from encrypted per-user accounts only in backend execution. Email bodies
are untrusted and excluded from audit metadata. See [Email integration](email-integration.md).

## Calendar

Calendar uses a provider-neutral tool/service/provider boundary with encrypted per-user OAuth
credentials. Reads are green and external content is untrusted. Create, update and cancel are
yellow, show a complete approval preview, verify the action fingerprint and reserve a durable
idempotency record before any provider call. Ambiguous write outcomes are not retried. See
[Calendar integration](calendar-integration.md).

## CRM foundation

CRM records are user-scoped and prepared for future workspace ownership. Reads are green;
mutations are yellow, exact-payload approved and idempotent. Email and Calendar links verify
ownership and store only provider references. Similar names never trigger automatic identity
merges. See [CRM foundation](crm-foundation.md).

## Client-management tools

Green reads: crm.list_clients, crm.get_client_360, crm.list_projects,
crm.list_pipelines, and crm.list_opportunities.

Yellow mutations: crm.create_client, crm.update_client, crm.create_project,
crm.update_project, crm.create_pipeline, crm.create_opportunity,
crm.update_opportunity, and crm.link_task. Commercial mutations are restricted to Sales;
Support may update projects and link tasks. Client insights always declare fact/model
provenance.

## Marketing tools

Green reads: marketing.list_campaigns, marketing.get_campaign, marketing.list_content,
marketing.get_content, marketing.list_content_calendar and marketing.list_metrics.

Yellow mutations: marketing.create_campaign, marketing.update_campaign,
marketing.create_content, marketing.update_content, marketing.transition_content,
marketing.schedule_content, marketing.record_publication, marketing.add_asset_metadata and
marketing.record_metric. No marketing.publish tool exists.
