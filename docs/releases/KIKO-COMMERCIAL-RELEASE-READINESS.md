# Kiko commercial release readiness

**Assessment date:** 2026-10-14  
**Release source revision:** `000466eec9f6cc6b4f2afd6ad18a97a7ed9045e9`  
**Migration head:** `20261014_0035`  
**Safety boundary:** local repository and isolated local PostgreSQL/Redis only; no staging or
production mutation and no real external-provider write.

## 1. Executive summary

The R0–R8 repository roadmap is complete. Kiko has moved from a substantial automation foundation
to a cohesive multi-tenant commercial release candidate with complete identity/workspace journeys,
governed operational modules, commercial controls, product surfaces, documentation, security
hardening, and automated release gates. The code is suitable for an **authorized isolated staging
deployment**. Production is not authorized because infrastructure, real-provider, registry-image,
human accessibility, legal, and operational gates require owner-controlled environments.

## 2. Baseline problems discovered

The baseline lacked a working deployed registration origin, canonical tenancy across business roots,
complete account/workspace lifecycle, onboarding, product navigation, several business workflows,
notifications/settings/commercial controls, E2E coverage, staging rehearsal, and a release package.
The preserved baseline and its original evidence are in `docs/audits/product-completion-baseline.md`.

## 3. Root cause of registration failure

The production browser bundle targeted the non-resolving `kiko.nodera.pt` API hostname while the
healthy service was reachable through the Kiko origin. The fix is a same-origin production API
contract; `NEXT_PUBLIC_API_URL` is development-only. No production build or data was changed.

## 4. Completed release phases

| Phase | Delivered result                                                                                  |
| ----- | ------------------------------------------------------------------------------------------------- |
| R0    | Audit, root-cause diagnosis, origin contract, migration/infrastructure baseline                   |
| R1    | Verification/recovery/sessions/profile, workspaces/RBAC/invitations/onboarding, canonical tenancy |
| R2    | Conversations, commands, plans, tasks/projects, Agent Center and governed approvals               |
| R3    | CRM, Marketing, Automations, safe Knowledge ingestion and integration reconciliation              |
| R4    | Notifications, activity, analytics, team/platform/settings, portability and retention             |
| R5    | Plans, entitlements, trials/subscription records and public commercial site                       |
| R6    | Unified responsive UI, accessible states, accurate readiness labels                               |
| R7    | Security/dependency hardening, E2E, PostgreSQL/Redis, migration, load and recovery evidence       |
| R8    | Synthetic demo, staging/test-account runbook, product/operator docs and release package           |

## 5. Final feature matrix

| Area                                   | Repository state                          | Staging gate                                   |
| -------------------------------------- | ----------------------------------------- | ---------------------------------------------- |
| Identity/workspaces/RBAC               | complete and tested                       | transactional email and human journey          |
| Kiko/work execution/approvals          | complete and governed                     | representative AI quality sample               |
| CRM/Marketing/Automations/Knowledge    | complete core lifecycles                  | provider-specific publication remains disabled |
| Notifications/analytics/admin/settings | complete                                  | alert routing/operator access                  |
| Plans/entitlements/billing abstraction | complete                                  | approved pricing and billing provider          |
| Integrations                           | fail-closed adapters and reconciliation   | real least-privilege test accounts             |
| Portability/retention                  | bounded export and conservative retention | legal policy approval                          |
| Public site/demo                       | complete synthetic experience             | timed human rehearsal in staging               |

## 6. Authentication test evidence

The backend suite covers normalized registration, Argon2id, verification/recovery token expiry and
one-shot behavior, non-enumeration, legal acceptance, access/refresh rotation and replay response,
session inventory/revocation, password change, profile/account state, throttling, and cookie rules.
Journey A passed in Chromium desktop and mobile against the real local API and PostgreSQL.

## 7. Workspace and role evidence

Owner/Admin/Manager/Member/Viewer permissions are enforced server-side. Invitations are expiring,
revocable and email-bound; ownership transfer and switching are tested. A browser/API adversarial
journey proved an outsider cannot list another workspace's invitations or read its CRM object.

## 8. AI execution evidence

Structured Supervisor/agent outputs, schema validation, risk classification, plan versioning,
approval fingerprints, idempotency, allowlists, audit, failure states, and conversation projections
are tested using deterministic fake providers. No real OpenAI request was made; representative
quality and cost evidence remains an authorized staging gate.

## 9. Integration test evidence

Six PostgreSQL/Redis tests passed: concurrent execution locking, outbox behavior, atomic OAuth-state
consumption, calendar-write race handling, automation deduplication, and cross-tenant CRM isolation.
Gmail, Calendar, SMTP, GitHub, Codex, and billing real-account tests were intentionally not run.

## 10. E2E results

Playwright: **6/6 passed** across desktop and mobile Chromium. Coverage includes registration,
login, onboarding, command-composer arrival, workspace membership boundary, CRM tenant boundary,
public responsive overflow, browser errors, unexpected HTTP failures, and Axe WCAG 2 A/AA serious
or critical violations. Vitest: **50 passed**. Next production build: **36 pages built**.

## 11. Security audit

The ASVS/API-oriented review found no remaining known BLOCKER or HIGH code-security defect. Production
OpenAPI is disabled; CSP and security headers are global; secrets use `SecretStr` until the provider
boundary; external writes remain approval/allowlist/idempotency governed. `pnpm audit --prod` and
`pip-audit` report no known dependency vulnerabilities after upgrades. Residual risks are documented
in `docs/security/security-review.md` and the known-limitations file.

## 12. Tenant-isolation audit

Business aggregate roots are workspace-scoped directly or inherit a validated workspace root.
Repositories/services resolve active membership and roles, and disclosure-sensitive foreign IDs
return not found. Unit/service tests plus real PostgreSQL and browser adversarial tests cover the
boundary. Staging must repeat the two-account procedure before provider activation.

## 13. Performance results

The bounded local API smoke issued **500 requests at concurrency 20 with 0 errors**: p50 18.10 ms,
p95 44.82 ms, p99 52.91 ms. These numbers validate regression behavior on one local machine and are
not production capacity claims. Staging must measure realistic datasets, workers and provider calls.

## 14. Migration status

Alembic has one linear head, `20261014_0035`. A clean PostgreSQL upgrade was completed; migration
0035 was downgraded to 0034 and upgraded again successfully. The migration job must run once before
application traffic. Prefer roll-forward when newer data makes downgrade unsafe.

## 15. Container build results

Both production Dockerfiles built successfully as non-root images. Local evidence IDs are API
`sha256:5fbd2e8b...b4a7b72` and Web `sha256:ee301732...214ee8`. They are local image IDs, not registry
digests. Authorized staging must rebuild the pinned source revision, scan, push, and record immutable
registry digests in the manifest before Compose interpolation can succeed.

## 16. Remaining limitations

Real providers, target infrastructure, registry digests, manual accessibility/usability, legal and
support gates remain. MFA is absent. Style CSP retains `unsafe-inline`. Full details and mitigations
are in `docs/releases/KIKO-KNOWN-LIMITATIONS.md`.

## 17. Known defects and severity

No known BLOCKER or HIGH repository defect remains. One LOW development warning remains: Starlette's
compatibility `TestClient` reports that its current httpx integration is deprecated. This does not
affect the production ASGI path. Any defect discovered in staging must reopen the release decision.

## 18. Production configuration requirements

Provide separate database/Redis credentials, authentication and encryption keys, trusted hosts and
proxy IPs, secure web origin, protected metrics token, secret-manager references, storage/queue
settings, and only the provider credentials explicitly approved. Use same-origin API routing, secure
cookies, TLS, private service networking, least-privilege runtime identities, and integrations off by
default. The names-only inventory is `.env.example`; never place values in the manifest.

## 19. Deployment procedure

Follow `docs/operations/staging-and-test-accounts.md`, then `docs/production-readiness.md`: pin source
and registry digests, scan, verify backup/restore, run the singleton migration, start dependencies and
services with providers disabled, require readiness, send canary traffic, run smoke/E2E/isolation,
observe signals, and enable only explicitly authorized providers one at a time.

## 20. Rollback procedure

Stop traffic expansion and external workers, restore the prior immutable application digests, and
verify readiness plus queues. Downgrade the database only if the exact migration was rehearsed and no
new writes would be lost; otherwise roll forward. Restore into an empty isolated database first,
verify checksum/head, and require incident-commander approval before a production restore.

## 21. Investor demo readiness

The reserved `sporting-cp-demo` workspace is explicitly flagged and visibly labelled synthetic. Its
idempotent seed creates fictional Knowledge, CRM, project/activity, campaign/content and a disabled
manual automation using `.invalid` domains. Reset requires the exact slug confirmation and refuses
unflagged workspaces. The seed/reset was rehearsed locally and a timed 12-minute script is documented.

## 22. Commercial readiness

Product code and documentation are ready for controlled staging. Commercial launch additionally
requires approved pricing/provider setup, legal/privacy review, support ownership, real provider
journeys, operational alerting/on-call, staging capacity evidence, and owner sign-off. The repository
does not claim those external decisions have occurred.

## 23. Final recommendation

Deploy revision `000466eec9f6cc6b4f2afd6ad18a97a7ed9045e9` only to a newly isolated, authorized staging
environment. Complete every manifest gate, archive evidence, and conduct a separate owner review
before considering production. No production action was performed by this roadmap run.

**READY FOR AUTHORIZED STAGING DEPLOYMENT**
